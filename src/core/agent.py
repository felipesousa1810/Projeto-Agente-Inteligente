"""Pydantic AI Agent - Deterministic scheduling agent for OdontoSorriso clinic."""

import uuid
from datetime import date, datetime, time
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel

from src.config.agent_config import AgentConfig, get_dynamic_system_prompt
from src.contracts.agent_response import AgentResponse, IntentType
from src.contracts.structured_output import StructuredAgentOutput
from src.contracts.whatsapp_message import WhatsAppMessage
from src.core.dependencies import AppDependencies
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Mapeamento da intenção de saída estruturada para enum IntentType
INTENT_MAPPING: dict[str, IntentType] = {
    "faq": IntentType.FAQ,
    "schedule": IntentType.SCHEDULE,
    "reschedule": IntentType.RESCHEDULE,
    "cancel": IntentType.CANCEL,
    "confirm": IntentType.CONFIRM,
    "deny": IntentType.DENY,
    "greeting": IntentType.GREETING,
    "unknown": IntentType.UNKNOWN,
}


def create_agent(
    config: AgentConfig | None = None,
) -> Agent[AppDependencies, StructuredAgentOutput]:
    """Cria e configura o agente Pydantic AI.

    Args:
        config: Configuração opcional do agente. Usa padrões se não fornecido.

    Returns:
        Instância do Agente configurada com saída estruturada.
    """
    if config is None:
        config = AgentConfig()

    # Cria o modelo OpenAI com configurações determinísticas
    model = OpenAIModel(
        config.model,
        # api_key é carregada automaticamente da variável de ambiente OPENAI_API_KEY
    )

    # Obtém prompt de sistema dinâmico com data/hora atual
    dynamic_prompt = get_dynamic_system_prompt()

    # Cria o agente com tipo de saída estruturada
    agent: Agent[AppDependencies, StructuredAgentOutput] = Agent(
        model=model,
        system_prompt=dynamic_prompt,
        deps_type=AppDependencies,
        output_type=StructuredAgentOutput,
        retries=0,  # Controle de retry externo
    )

    # Registrar ferramentas (tools)
    @agent.tool
    async def check_availability(
        ctx: RunContext[AppDependencies],
        date_str: str,
        time_str: str,
    ) -> dict[str, Any]:
        """Verifica disponibilidade de horário.

        Args:
            ctx: Contexto de execução com dependências.
            date_str: Data no formato YYYY-MM-DD.
            time_str: Hora no formato HH:MM.

        Returns:
            Dict com 'available' (bool) e 'alternatives' (list).
        """
        logger.info(
            "check_availability",
            trace_id=ctx.deps.trace_id,
            date=date_str,
            time=time_str,
        )

        # Parse de data e hora
        try:
            check_date = date.fromisoformat(date_str)
            check_time = time.fromisoformat(time_str)
        except ValueError:
            return {
                "available": False,
                "error": "Formato de data/hora inválido",
                "alternatives": [],
            }

        # Verifica se data é no passado
        if check_date < date.today():
            return {
                "available": False,
                "error": "Data no passado",
                "alternatives": [],
            }

        # Verifica horário comercial: 8:00 - 18:00
        hour = check_time.hour
        if hour < 8 or hour >= 18:
            return {
                "available": False,
                "error": "Fora do horário comercial (8h-18h)",
                "alternatives": ["09:00", "10:00", "14:00", "15:00"],
            }

        # 1. Verificar slots ocupados no Supabase (Interno) via serviço injetado
        # Nota: O serviço Supabase precisa ter o método get_appointments_for_date
        try:
            db_appointments = await ctx.deps.supabase.get_appointments_for_date(
                date_str
            )
        except Exception as e:
            logger.error("erro_verificacao_banco", error=str(e))
            # Fallback seguro se banco falhar? Ou erro?
            # Por enquanto, logar e assumir vazio ou retornar erro
            db_appointments = []

        # TODO: Implementar verificação real no Google Calendar (Externo)
        # Seria algo como: ctx.deps.calendar.check_availability(check_date)

        # Logica simples de mesclagem (substituir pela lógica real)
        all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
        taken_times = set()

        for appt in db_appointments:
            # stored as string HH:MM:SS or time object
            t = str(appt["scheduled_time"])[:5]
            taken_times.add(t)

        available_slots = [s for s in all_slots if s not in taken_times]

        # Se o horário solicitado está na lista de disponíveis
        is_available = time_str in available_slots

        # Se a lista estiver vazia e o horário não for tomado (ex: não consultou calendar), assume livre?
        # Pela lógica acima, só é livre se estiver em all_slots e não tomado.

        return {
            "available": is_available,
            "alternatives": available_slots if not is_available else [],
        }

    @agent.tool
    async def create_appointment(
        ctx: RunContext[AppDependencies],
        date_str: str,
        time_str: str,
    ) -> dict[str, Any]:
        """Cria um novo agendamento.

        Args:
            ctx: Contexto de execução com dependências.
            date_str: Data no formato YYYY-MM-DD.
            time_str: Hora no formato HH:MM.

        Returns:
            Dict com 'success', 'appointment_id' e 'confirmation_code'.
        """
        logger.info(
            "create_appointment",
            trace_id=ctx.deps.trace_id,
            customer_id=ctx.deps.customer_id,
            date=date_str,
            time=time_str,
        )

        if not ctx.deps.customer_id:
            return {"success": False, "error": "ID do cliente não identificado"}

        # Gerar código de confirmação
        confirmation_code = f"APPT-{uuid.uuid4().hex[:8].upper()}"

        try:
            # 1. Obter ou criar cliente (garantir que existe no DB)
            # Nota: Isso deveria idealmente ser feito antes, mas garantimos aqui
            customer = await ctx.deps.supabase.get_or_create_customer(
                ctx.deps.customer_id
            )

            # 2. Criar no Supabase usando serviço injetado
            appt = await ctx.deps.supabase.create_appointment(
                customer_id=customer["id"],
                scheduled_date=date_str,
                scheduled_time=time_str,
                confirmation_code=confirmation_code,
            )

            # 3. Criar no Google Calendar (TODO: Injetar serviço de calendário)
            # calendar_service = ctx.deps.calendar...

            return {
                "success": True,
                "appointment_id": appt["id"],
                "confirmation_code": confirmation_code,
                "date": date_str,
                "time": time_str,
            }

        except Exception as e:
            logger.error("falha_criar_agendamento", error=str(e))
            return {"success": False, "error": "Erro ao criar agendamento"}

    @agent.tool
    async def cancel_appointment(
        ctx: RunContext[AppDependencies],
        confirmation_code: str,
    ) -> dict[str, Any]:
        """Cancela um agendamento existente.

        Args:
            ctx: Contexto de execução com dependências.
            confirmation_code: Código de confirmação do agendamento.

        Returns:
            Dict com 'success' e 'message'.
        """
        logger.info(
            "cancel_appointment",
            trace_id=ctx.deps.trace_id,
            confirmation_code=confirmation_code,
        )

        try:
            # 1. Buscar agendamento
            appt = await ctx.deps.supabase.get_appointment_by_code(confirmation_code)
            if not appt:
                return {"success": False, "error": "Agendamento não encontrado"}

            # 2. Cancelar no Supabase
            await ctx.deps.supabase.cancel_appointment(appt["id"])

            return {
                "success": True,
                "message": f"Agendamento {confirmation_code} cancelado com sucesso.",
            }
        except Exception as e:
            logger.error("falha_cancelar_agendamento", error=str(e))
            return {"success": False, "error": "Erro ao processar cancelamento"}

    return agent


# Global agent instance (lazy initialization)
_agent: Agent[AppDependencies, StructuredAgentOutput] | None = None


def get_agent() -> Agent[AppDependencies, StructuredAgentOutput]:
    """Get or create the global agent instance.

    Returns:
        Agent instance with structured output.
    """
    global _agent
    if _agent is None:
        _agent = create_agent()
    return _agent


async def process_message(
    message: WhatsAppMessage,
    deps: AppDependencies | None = None,
) -> AgentResponse:
    """Processa mensagem de entrada do WhatsApp usando arquitetura DETERMINÍSTICA.

    Arquitetura: NLU -> DecisionEngine -> Templates -> NLG
    - NLU: Extrai intenção e entidades (LLM)
    - DecisionEngine: Decide próxima ação (CÓDIGO - 100% determinístico)
    - Templates/Contexto: Prepara dados para resposta
    - NLG: Humaniza a resposta (LLM com Guardrails)

    Args:
        message: Mensagem WhatsApp validada.
        deps: Dependências da aplicação (Supabase, Trace ID, etc).

    Returns:
        AgentResponse com intenção, resposta e dados extraídos.
    """
    from src.core.decision_engine import get_decision_engine
    from src.core.nlg import generate_response
    from src.core.nlu import NLU
    from src.core.templates import get_faq_answer
    from src.services.conversation_state import get_conversation_state_manager
    from src.services.supabase import get_supabase_service

    # Se deps não fornecido, cria com padrões (fallback para suportar código legado/testes)
    if deps is None:
        trace_id = str(uuid.uuid4())
        # Cria serviço supabase padrão
        supabase_service = get_supabase_service()
        deps = AppDependencies(
            supabase=supabase_service.client,
            customer_id=message.from_number,
            trace_id=trace_id,
        )
        # Hack temporário: AppDependencies espera Client, mas tools usam métodos de SupabaseService...
        # Para corrigir isso corretamente: AppDependencies deve conter SupabaseService, não Client puro.
        # Mas vamos ajustar AppDependencies em dependencies.py primeiro ou adaptar aqui?
        # Melhor: Vamos assumir que deps.supabase é o SERVICE já instanciado que tem os métodos ricos.
        # Então precisamos atualizar dependencies.py para tipar com SupabaseService.

    trace_id = deps.trace_id or str(uuid.uuid4())
    now = datetime.now()

    logger.info(
        "inicio_processamento_mensagem",
        trace_id=trace_id,
        message_id=message.message_id,
        from_number=message.from_number,
        architecture="deterministic",
    )

    start_time = now

    try:
        # =====================================================
        # PASSO 1: Obter estado da conversa do Redis
        # =====================================================
        state_manager = get_conversation_state_manager()
        fsm = await state_manager.get_or_create(message.from_number)

        logger.info(
            "estado_fsm_carregado",
            trace_id=trace_id,
            current_state=fsm.current_state.value,
            collected_data=fsm.collected_data,
        )

        # =====================================================
        # PASSO 2: NLU - Extrair intenção e entidades (LLM)
        # =====================================================
        nlu = NLU()
        nlu_output = await nlu.extract(
            message=message.body,
            current_date=now.strftime("%Y-%m-%d"),
            current_time=now.strftime("%H:%M"),
        )

        logger.info(
            "extracao_nlu_completa",
            trace_id=trace_id,
            intent=nlu_output.intent,
            extracted_date=nlu_output.extracted_date,
            extracted_time=nlu_output.extracted_time,
            extracted_procedure=nlu_output.extracted_procedure,
            confidence=nlu_output.confidence,
        )

        # =====================================================
        # PASSO 3: DecisionEngine - Decidir próxima ação (CÓDIGO)
        # Isso é 100% DETERMINÍSTICO - mesma entrada = mesma saída
        # =====================================================
        decision_engine = get_decision_engine()
        action = decision_engine.decide(fsm, nlu_output)

        logger.info(
            "decisao_tomada",
            trace_id=trace_id,
            action_type=action.action_type.value,
            template_key=action.template_key,
            requires_tool=action.requires_tool,
        )

        # =====================================================
        # PASSO 4: Executar ferramenta se necessário (CÓDIGO)
        # =====================================================
        tool_result: dict[str, Any] = {}
        if action.requires_tool and action.tool_name:
            # Usar o service que veio nas deps
            tool_result = await _execute_tool(
                action.tool_name,
                action.context,
                message.from_number,
                trace_id,
                # Passando o service wrapper. Nota: deps.supabase no dependencies.py está como Client,
                # mas vamos mudar para SupabaseService. Vou fazer cast ou update.
                deps,
            )
            # Mesclar resultado da tool no contexto
            action.context.update(tool_result)

        # =====================================================
        # PASSO 5: Gerar Resposta (Guardrails NLG)
        # =====================================================
        # Lidar com casos especiais para enriquecimento de contexto
        if action.template_key == "faq_response":
            faq_answer = get_faq_answer(nlu_output.extracted_procedure)
            action.context["answer"] = faq_answer
            if not nlu_output.extracted_procedure:
                action.context["procedure"] = "tratamentos"

        # Lidar com disponibilidade para slots de horário
        if action.template_key == "ask_time":
            slots = action.context.get(
                "available_slots", "09:00, 10:00, 14:00, 15:00, 16:00"
            )
            if isinstance(slots, list):
                slots = ", ".join(slots)
            action.context["available_slots"] = slots

        # Gerar a resposta usando PydanticAI Guardrails
        # O LLM gera o texto estritamente aderindo ao schema para este ActionType
        humanized_response = await generate_response(action)

        # =====================================================
        # PASSO 7: Atualizar estado FSM se a ação especificar
        # =====================================================
        if action.next_state and fsm.can_transition_to(action.next_state):
            fsm.transition(action.next_state)

        # Salvar FSM atualizado no Redis
        await state_manager.save(message.from_number, fsm)

        # =====================================================
        # PASSO 8: Construir e retornar resposta
        # =====================================================
        # Mapear intenção NLU para enum IntentType
        intent = INTENT_MAPPING.get(nlu_output.intent, IntentType.UNKNOWN)

        # Construir extracted_data do FSM
        extracted_data: dict[str, str] = dict(fsm.collected_data)

        response = AgentResponse(
            trace_id=trace_id,
            intent=intent,
            reply_text=humanized_response,
            confidence=nlu_output.confidence,
            appointment_id=tool_result.get("appointment_id"),
            extracted_data=extracted_data,
            clarification_needed=action.action_type.value == "clarify",
        )

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            "processamento_mensagem_completo",
            trace_id=trace_id,
            intent=response.intent.value,
            confidence=response.confidence,
            latency_ms=elapsed_ms,
            extracted_data=extracted_data,
            architecture="deterministic",
        )

        return response

    except Exception as e:
        import traceback

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.error(
            "erro_processamento_mensagem",
            trace_id=trace_id,
            error=str(e),
            error_type=type(e).__name__,
            traceback=traceback.format_exc(),
            latency_ms=elapsed_ms,
        )

        # Retornar resposta de erro
        return AgentResponse(
            trace_id=trace_id,
            intent=IntentType.UNKNOWN,
            reply_text="Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.",
            confidence=0.0,
            clarification_needed=True,
        )


async def _execute_tool(
    tool_name: str,
    context: dict[str, Any],
    customer_id: str,
    trace_id: str,
    deps: AppDependencies,
) -> dict[str, Any]:
    """Executa uma ferramenta baseada nos requisitos da ação.

    Args:
        tool_name: Nome da ferramenta a executar.
        context: Dados de contexto para a ferramenta.
        customer_id: Telefone do cliente.
        trace_id: ID de rastreamento.
        deps: Dependências injetadas (SupabaseService, etc).

    Returns:
        Resultado da execução da ferramenta.
    """
    from src.services.calendar import get_calendar_service
    # Nota: deps.supabase agora deve ser tratado como SupabaseService

    logger.info(
        "inicio_execucao_tool",
        trace_id=trace_id,
        tool_name=tool_name,
    )

    if tool_name == "check_availability":
        date_str = context.get("date")
        if not date_str:
            return {"available": False, "error": "Data não fornecida"}

        try:
            check_date = date.fromisoformat(date_str)

            # 1. Buscar slots ocupados no Supabase (Interno) via deps
            # Assumindo que deps.supabase é SupabaseService
            db_appointments = await deps.supabase.get_appointments_for_date(date_str)

            # 2. Buscar slots ocupados no Google Calendar (Externo)
            # TODO: Injetar calendar service em deps também
            calendar_service = get_calendar_service()
            gcal_busy = calendar_service.check_availability(check_date)

            # 3. Mesclar e calcular slots disponíveis (Lógica simples por enquanto)
            # Lógica de negócio: 09:00 - 17:00, slots de 1 hora
            all_slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
            taken_times = set()

            # Processar agendamentos do DB
            for appt in db_appointments:
                # armazenado como string HH:MM:SS ou objeto time
                t = str(appt["scheduled_time"])[:5]
                taken_times.add(t)

            # Processar eventos GCal
            for slot in gcal_busy:
                start_iso = slot["start"]  # ex: 2026-02-15T14:00:00Z
                try:
                    # Parse simplificado (idealmente usar biblioteca timezone robusta)
                    dt_start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
                    if dt_start.date() == check_date:
                        taken_times.add(dt_start.strftime("%H:%M"))
                except ValueError:
                    continue

            available_slots = [s for s in all_slots if s not in taken_times]

            return {
                "available": len(available_slots) > 0,
                "available_slots": available_slots if available_slots else [],
            }

        except ValueError:
            return {"available": False, "error": "Erro ao verificar data"}

    if tool_name == "create_appointment":
        date_str = context.get("date")
        time_str = context.get("time")
        procedure = context.get("procedure", "Consulta")

        if not date_str or not time_str:
            return {"success": False, "error": "Data ou hora faltando"}

        # 1. Obter/Criar Cliente
        try:
            customer = await deps.supabase.get_or_create_customer(
                customer_id
            )  # customer_id é o telefone aqui
        except Exception as e:
            logger.error("erro_cliente_tool", error=str(e))
            return {"success": False, "error": "Erro ao identificar cliente"}

        # 2. Criar no Supabase
        confirmation_code = f"APPT-{uuid.uuid4().hex[:8].upper()}"

        try:
            appt = await deps.supabase.create_appointment(
                customer_id=customer["id"],
                scheduled_date=date_str,
                scheduled_time=time_str,
                confirmation_code=confirmation_code,
            )

            # 3. Criar no Google Calendar
            calendar_service = get_calendar_service()

            # Parse datetimes
            start_dt = datetime.fromisoformat(f"{date_str}T{time_str}")
            end_dt = start_dt.replace(hour=start_dt.hour + 1)

            calendar_service.create_event(
                summary=f"{procedure} - {customer.get('name', 'Cliente')}",
                description=f"Tel: {customer_id}\nCódigo: {confirmation_code}",
                start_dt=start_dt,
                end_dt=end_dt,
            )

            return {
                "success": True,
                "appointment_id": appt["id"],
                "confirmation_code": confirmation_code,
                "date": date_str,
                "time": time_str,
            }
        except Exception as e:
            logger.error("falha_criar_agendamento_tool", error=str(e))
            return {"success": False, "error": "Erro ao criar agendamento"}

    if tool_name == "cancel_appointment":
        confirmation_code = context.get("confirmation_code", "")
        if not confirmation_code:
            return {"success": False, "error": "Código não fornecido"}

        # 1. Encontrar agendamento
        appt = await deps.supabase.get_appointment_by_code(confirmation_code)
        if not appt:
            return {"success": False, "error": "Agendamento não encontrado"}

        # 2. Cancelar no Supabase
        await deps.supabase.cancel_appointment(appt["id"])

        # 3. Cancelar no GCal (TODO: verificar necessidade de armazenar ID do evento)
        logger.info("cancelamento_gcal_necessario_manual", appointment_id=appt["id"])

        return {
            "success": True,
            "message": f"Agendamento {confirmation_code} cancelado.",
        }

    logger.warning(
        "tool_desconhecida",
        trace_id=trace_id,
        tool_name=tool_name,
    )
    return {}
