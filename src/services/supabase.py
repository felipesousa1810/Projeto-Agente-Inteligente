"""Serviço do Supabase - Operações de Banco de Dados."""

from typing import Any

from src.config.settings import get_settings
from src.utils.logger import get_logger
from supabase import Client, create_client

logger = get_logger(__name__)


class SupabaseService:
    """Serviço encapsulado para operações no Supabase."""

    def __init__(self, client: Client | None = None) -> None:
        """Inicializa o serviço com um cliente Supabase.

        Args:
            client: Cliente Supabase opcional. Se não fornecido, cria um novo base nas settings.
        """
        if client:
            self.client = client
        else:
            self.client = self._create_client()

    def _create_client(self) -> Client:
        """Cria um novo cliente Supabase a partir das configurações."""
        settings = get_settings()

        # Prioriza a service key para operações de backend para ignorar RLS (Row Level Security)
        key = settings.supabase_service_key or settings.supabase_key

        if not key:
            logger.warning(
                "supabase_not_configured",
                message="Credenciais do Supabase não configuradas. Operações de banco falharão.",
            )
            if settings.is_development:
                logger.info(
                    "supabase_mock_mode", message="Usando modo mock em desenvolvimento"
                )
            else:
                raise ValueError("Credenciais do Supabase são obrigatórias em produção")
            # Retorna um cliente dummy ou falha, dependendo da lib, aqui retornamos o create_client mesmo que falhe depois
            # Mas o pydantic settings normalmente garante que url existe se não for optional

        # Cria o cliente
        new_client = create_client(settings.supabase_url, key)

        logger.info(
            "supabase_client_created",
            using_service_key=key == settings.supabase_service_key,
            key_preview=key[:5] + "..." if key else "None",
        )
        return new_client

    async def get_or_create_customer(self, phone_number: str) -> dict[str, Any]:
        """Busca cliente existente ou cria um novo.

        Args:
            phone_number: Telefone do cliente no formato E.164.

        Returns:
            Dicionário com dados do cliente.
        """
        # Tenta encontrar cliente existente (Safer approach: limit(1) para evitar erro 406 em duplicatas)
        try:
            result = (
                self.client.table("customers")
                .select("*")
                .eq("phone_number", phone_number)
                .limit(1)
                .execute()
            )

            # Verifica se retornou dados
            if result and result.data and len(result.data) > 0:
                logger.info(
                    "customer_found",
                    customer_id=result.data[0]["id"],
                    phone_number=phone_number,
                )
                return result.data[0]

        except Exception as e:
            logger.warning("customer_lookup_error", error=str(e))
            # Prossegue para criação se busca falhou (exceção silenciosa aqui, melhor logar e tentar criar)
            pass

        # Cria novo cliente
        try:
            new_customer = {"phone_number": phone_number}
            result = self.client.table("customers").insert(new_customer).execute()

            if result and result.data:
                logger.info(
                    "customer_created",
                    customer_id=result.data[0]["id"],
                    phone_number=phone_number,
                )
                return result.data[0]
            else:
                raise ValueError("Falha ao criar cliente: Nenhum dado retornado")

        except Exception as e:
            # Se a criação falhar (ex: condição de corrida criando ao mesmo tempo), tenta buscar novamente
            logger.warning("customer_creation_failed_retrying_fetch", error=str(e))

            result = (
                self.client.table("customers")
                .select("*")
                .eq("phone_number", phone_number)
                .limit(1)
                .execute()
            )
            if result and result.data:
                return result.data[0]

            raise e

    async def save_message(
        self,
        message_id: str,
        customer_id: str,
        direction: str,
        body: str,
        intent: str | None,
        trace_id: str,
    ) -> dict[str, Any]:
        """Salva mensagem no banco de dados.

        Args:
            message_id: ID único da mensagem.
            customer_id: UUID do cliente.
            direction: 'incoming' (entrada) ou 'outgoing' (saída).
            body: Texto da mensagem.
            intent: Intenção detectada (para mensagens de entrada).
            trace_id: ID de rastreamento.

        Returns:
            Registro da mensagem salva.
        """
        message_data = {
            "message_id": message_id,
            "customer_id": customer_id,
            "direction": direction,
            "body": body,
            "intent": intent,
            "trace_id": trace_id,
        }

        result = self.client.table("messages").insert(message_data).execute()

        logger.info(
            "message_saved",
            message_id=message_id,
            direction=direction,
            trace_id=trace_id,
        )
        return result.data[0]

    async def create_appointment(
        self,
        customer_id: str,
        scheduled_date: str,
        scheduled_time: str,
        confirmation_code: str,
    ) -> dict[str, Any]:
        """Cria agendamento no banco de dados.

        Args:
            customer_id: UUID do cliente.
            scheduled_date: Data no formato YYYY-MM-DD.
            scheduled_time: Hora no formato HH:MM.
            confirmation_code: Código de confirmação único.

        Returns:
            Registro do agendamento criado.
        """
        appointment_data = {
            "customer_id": customer_id,
            "scheduled_date": scheduled_date,
            "scheduled_time": scheduled_time,
            "status": "scheduled",
            "confirmation_code": confirmation_code,
        }

        result = self.client.table("appointments").insert(appointment_data).execute()

        logger.info(
            "appointment_created",
            appointment_id=result.data[0]["id"],
            confirmation_code=confirmation_code,
        )
        return result.data[0]

    async def get_appointment_by_code(
        self, confirmation_code: str
    ) -> dict[str, Any] | None:
        """Busca agendamento pelo código de confirmação.

        Args:
            confirmation_code: Código de confirmação único.

        Returns:
            Registro do agendamento ou None se não encontrado.
        """
        result = (
            self.client.table("appointments")
            .select("*")
            .eq("confirmation_code", confirmation_code)
            .maybe_single()
            .execute()
        )

        return result.data

    async def cancel_appointment(self, appointment_id: str) -> dict[str, Any]:
        """Cancela agendamento pelo ID.

        Args:
            appointment_id: UUID do agendamento.

        Returns:
            Registro do agendamento atualizado.
        """
        result = (
            self.client.table("appointments")
            .update({"status": "canceled"})
            .eq("id", appointment_id)
            .execute()
        )

        logger.info(
            "appointment_canceled",
            appointment_id=appointment_id,
        )
        return result.data[0]

    async def get_appointments_for_date(self, check_date: str) -> list[dict[str, Any]]:
        """Busca todos os agendamentos para uma data específica.

        Args:
            check_date: Data no formato YYYY-MM-DD.

        Returns:
            Lista de agendamentos.
        """
        result = (
            self.client.table("appointments")
            .select("*")
            .eq("scheduled_date", check_date)
            .neq("status", "canceled")  # Exclui agendamentos cancelados
            .execute()
        )

        logger.info(
            "appointments_fetched_for_date",
            date=check_date,
            count=len(result.data),
        )
        return result.data


# Instância global para retrocompatibilidade (se necessário), mas idealmente usar DI
_supabase_service: SupabaseService | None = None


def get_supabase_service() -> SupabaseService:
    """Retorna ou cria instância global do serviço.

    Útil para partes do código que ainda não usam injeção de dependência completa.
    """
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service
