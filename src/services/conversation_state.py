"""Conversation State Manager - Gerencia estado de conversa por usuário.

Mantém contexto de conversa no Redis, permitindo que o agente
lembre informações já coletadas entre mensagens.
"""

import json
from typing import Any

import redis.asyncio as redis

from src.core.fsm import AppointmentState, StateMachine
from src.utils.logger import get_logger

logger = get_logger(__name__)

# TTL para estado de conversa: 1 hora (expira se usuário parar de responder)
CONVERSATION_TTL_SECONDS = 3600


class ConversationStateManager:
    """Gerencia estado de conversa por usuário no Redis.

    Permite manter contexto entre mensagens, armazenando:
    - Estado atual do fluxo (FSM)
    - Dados coletados (procedimento, data, hora)
    - Histórico de estados
    """

    def __init__(self, redis_url: str) -> None:
        """Inicializa o gerenciador.

        Args:
            redis_url: URL de conexão do Redis.
        """
        self.redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def _get_redis(self) -> redis.Redis:
        """Obtém conexão Redis (lazy init)."""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
        return self._redis

    def _key(self, phone: str) -> str:
        """Gera chave Redis para o usuário."""
        return f"conversation:{phone}"

    async def get_or_create(self, phone: str) -> StateMachine:
        """Recupera ou cria FSM para o usuário.

        Args:
            phone: Número de telefone do usuário.

        Returns:
            StateMachine com estado atual ou nova.
        """
        try:
            r = await self._get_redis()
            key = self._key(phone)
            data = await r.get(key)

            if data:
                # Recuperar estado existente
                state_dict = json.loads(data)
                fsm = StateMachine(
                    customer_id=phone,
                    current_state=AppointmentState(state_dict.get("current_state", "initiated")),
                    collected_data=state_dict.get("collected_data", {}),
                    history=[AppointmentState(s) for s in state_dict.get("history", [])],
                )
                logger.info(
                    "conversation_state_loaded",
                    phone=phone,
                    state=fsm.current_state.value,
                    collected_data=fsm.collected_data,
                )
                return fsm

        except Exception as e:
            logger.warning(
                "conversation_state_load_failed",
                phone=phone,
                error=str(e),
            )

        # Criar novo estado
        return StateMachine(customer_id=phone)

    async def save(self, phone: str, fsm: StateMachine) -> None:
        """Persiste estado no Redis.

        Args:
            phone: Número de telefone do usuário.
            fsm: StateMachine a ser salva.
        """
        try:
            r = await self._get_redis()
            key = self._key(phone)

            state_dict = {
                "current_state": fsm.current_state.value,
                "collected_data": fsm.collected_data,
                "history": [s.value for s in fsm.history],
            }

            await r.setex(key, CONVERSATION_TTL_SECONDS, json.dumps(state_dict))

            logger.info(
                "conversation_state_saved",
                phone=phone,
                state=fsm.current_state.value,
                collected_data=fsm.collected_data,
            )

        except Exception as e:
            logger.warning(
                "conversation_state_save_failed",
                phone=phone,
                error=str(e),
            )

    async def clear(self, phone: str) -> None:
        """Limpa estado da conversa (após agendamento completo).

        Args:
            phone: Número de telefone do usuário.
        """
        try:
            r = await self._get_redis()
            await r.delete(self._key(phone))
            logger.info("conversation_state_cleared", phone=phone)
        except Exception as e:
            logger.warning(
                "conversation_state_clear_failed",
                phone=phone,
                error=str(e),
            )

    def build_context_prompt(self, fsm: StateMachine) -> str:
        """Gera contexto para injetar no prompt do agente.

        Args:
            fsm: StateMachine com dados coletados.

        Returns:
            String com contexto formatado para o LLM.
        """
        if not fsm.collected_data:
            return ""

        lines = ["## 📋 Contexto da Conversa (DADOS JÁ COLETADOS - NÃO PERGUNTE NOVAMENTE!)"]

        data_labels = {
            "procedure": "Procedimento",
            "date": "Data",
            "time": "Horário",
            "name": "Nome",
        }

        for key, value in fsm.collected_data.items():
            label = data_labels.get(key, key.title())
            lines.append(f"- **{label}:** {value}")

        lines.append("")
        lines.append("⚠️ USE os dados acima. NÃO pergunte o que já foi informado!")
        lines.append("")

        return "\n".join(lines)


# Singleton instance
_state_manager: ConversationStateManager | None = None


def get_conversation_state_manager() -> ConversationStateManager:
    """Obtém instância singleton do gerenciador.

    Returns:
        ConversationStateManager configurado.
    """
    global _state_manager
    if _state_manager is None:
        from src.config.settings import get_settings
        settings = get_settings()
        _state_manager = ConversationStateManager(redis_url=settings.redis_url)
    return _state_manager
