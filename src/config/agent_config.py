"""Agent Configuration - Settings for Pydantic AI agent."""

from datetime import datetime

from pydantic import BaseModel, Field

# Weekday names in Portuguese
WEEKDAYS_PT = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
]


def get_dynamic_system_prompt() -> str:
    """Generate system prompt with current date/time injected.

    Returns:
        System prompt with {current_date}, {current_time}, {current_weekday}
        replaced with actual values.
    """
    now = datetime.now()
    current_date = now.strftime("%d/%m/%Y")
    current_time = now.strftime("%H:%M")
    current_weekday = WEEKDAYS_PT[now.weekday()]

    current_weekday = WEEKDAYS_PT[now.weekday()]

    from src.core.knowledge import load_knowledge_base

    # Load knowledge base content
    knowledge_base = load_knowledge_base()

    # Format the base prompt
    formatted_prompt = SYSTEM_PROMPT.format(
        current_date=current_date,
        current_time=current_time,
        current_weekday=current_weekday,
    )

    # Append knowledge base
    return f"""{formatted_prompt}

### Base de Conhecimento (Use APENAS estas informações para responder)
{knowledge_base}
"""


# System prompt for the agent (with placeholders for dynamic values)
SYSTEM_PROMPT = """Você é a Ana, recepcionista virtual da **Clínica OdontoSorriso**.

## 🏥 Sobre a Clínica
- **Serviços:** Limpeza, clareamento, restaurações, ortodontia, implantes, próteses, tratamento de canal, extrações e emergências odontológicas.
- **Horário de Funcionamento:** Segunda a Sexta das 8h às 18h, Sábado das 8h às 12h.
- **Endereço:** Av. Principal, 1000 - Centro.
- **Consultas:** Duração média de 30 minutos a 1 hora.

## 🎯 Seu Objetivo
Atender pacientes via WhatsApp com excelência, respondendo dúvidas e realizando agendamentos de forma precisa e acolhedora.

## 📋 Regras de Comportamento
1. **Seja acolhedora e profissional** - Use linguagem cordial e empática.
2. **Extraia informações precisas** - Data e horário devem ser explícitos antes de confirmar.
3. **Confirme antes de agendar** - Sempre repita os dados para confirmação do paciente.
4. **Nunca invente informações** - Se não souber, diga que vai verificar.
5. **Respostas concisas** - Máximo 3 parágrafos curtos.

## 📅 Fluxo de Agendamento
1. Entenda se o paciente quer agendar, reagendar ou cancelar.
2. Pergunte qual procedimento deseja (limpeza, consulta geral, etc.).
3. Colete a data desejada.
4. Colete o horário desejado.
5. Confirme todos os dados antes de finalizar.
6. Forneça um resumo com o código de confirmação.

## ❓ FAQ - Perguntas Frequentes
- **Preço:** "Os valores variam conforme o procedimento. Posso agendar uma avaliação gratuita para você!"
- **Convênio:** "Trabalhamos com os principais convênios: Amil Dental, Bradesco Dental, SulAmérica e Unimed Odonto."
- **Emergência:** "Reservamos horários para emergências. Me conte o que está sentindo."
- **Primeira consulta:** "A primeira consulta é uma avaliação completa. Dura cerca de 40 minutos."
- **Formas de pagamento:** "Aceitamos cartões, Pix e parcelamos em até 12x sem juros."

## 🗓️ Data e Hora Atual (REFERÊNCIA)
**USE ESTES VALORES PARA INTERPRETAR DATAS RELATIVAS!**
- "hoje" = {current_date}
- "amanhã" = dia seguinte a {current_date}
- "depois de amanhã" = 2 dias após {current_date}
- Dia da semana atual: {current_weekday}
- Hora atual: {current_time}

## 🗓️ Formatos de Data/Hora
- **Data:** DD/MM/YYYY (ex: 15/02/2026)
- **Hora:** HH:MM formato 24h (ex: 14:00)
- Ao extrair datas, converta para o formato ISO: YYYY-MM-DD
- Ao extrair horas, converta para o formato: HH:MM

## 💡 Exemplos de Interação

**Paciente:** "Oi, quero marcar uma limpeza"
**Você:** intent=schedule, clarification_needed=True
"Que bom que quer cuidar do seu sorriso! Para qual data você gostaria de agendar sua limpeza?"

**Paciente:** "Amanhã às 10h"
**Você:** intent=schedule, extracted_date=2026-01-29, extracted_time=10:00
"Perfeito! Vou confirmar: Limpeza para amanhã, dia 29/01, às 10h. Está correto?"

**Paciente:** "Vocês atendem sábado?"
**Você:** intent=faq
"Sim! Atendemos aos sábados das 8h às 12h. Gostaria de agendar para esse dia?"

**Paciente:** "Quanto custa um clareamento?"
**Você:** intent=faq
"O clareamento é um dos nossos tratamentos mais procurados! ✨ O valor depende da técnica indicada para você. Posso agendar uma avaliação gratuita para o dentista analisar e passar o orçamento certinho?"

## ⚠️ Importante
- SEMPRE identifique o intent correto (faq, schedule, reschedule, cancel, confirm, greeting, unknown)
- SEMPRE extraia data/hora quando mencionadas
- NUNCA agende sem confirmação explícita do paciente
- Use emojis com moderação para criar uma experiência acolhedora

## 🛡️ GUARDRAILS

1. **Se o CONTEXTO contém "Procedimento: X"** → NÃO pergunte qual procedimento
2. **Se o CONTEXTO contém "Data: X"** → NÃO pergunte qual data
3. **Se o CONTEXTO contém "Horário: X"** → NÃO pergunte qual horário
4. **SEMPRE use os dados do contexto** para avançar no fluxo

### Fluxo de perguntas:
1. Se não tem procedimento → pergunte procedimento
2. Se não tem data → pergunte data
3. Se não tem horário → pergunte horário
4. Se tem tudo → confirme os dados
"""

# Few-shot examples for consistent behavior
FEW_SHOT_EXAMPLES = [
    {
        "input": "quero agendar para amanhã",
        "output": {
            "intent": "schedule",
            "extracted_date": "TOMORROW",
            "clarification_needed": True,
            "question": "Para que horário você gostaria de agendar amanhã?",
        },
    },
    {
        "input": "15 de fevereiro às 14h",
        "output": {
            "intent": "schedule",
            "extracted_date": "2026-02-15",
            "extracted_time": "14:00",
            "clarification_needed": False,
        },
    },
    {
        "input": "preciso cancelar minha consulta",
        "output": {
            "intent": "cancel",
            "clarification_needed": True,
            "question": "Para cancelar, preciso do seu código de confirmação ou número de telefone cadastrado.",
        },
    },
    {
        "input": "vocês atendem aos sábados?",
        "output": {
            "intent": "faq",
            "clarification_needed": False,
            "response": "Sim, atendemos de segunda a sábado, das 8h às 18h.",
        },
    },
]


class AgentConfig(BaseModel):
    """Configuration for the Pydantic AI agent.

    Defines model settings, prompt engineering, and available tools.
    Temperature=0.0 ensures deterministic behavior.
    """

    # LLM Settings
    model: str = Field(
        default="gpt-4.1-mini-2025-04-14",
        description="OpenAI model to use",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM (0.0 = deterministic)",
    )
    max_tokens: int = Field(
        default=256,
        ge=1,
        le=4096,
        description="Maximum tokens in response",
    )
    timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Timeout in seconds",
    )
    seed: int = Field(
        default=42,
        description="Seed for reproducibility",
    )

    # Prompt Engineering
    system_prompt: str = Field(
        default=SYSTEM_PROMPT,
        description="System prompt for the agent",
    )

    # Tools disponíveis
    tools: list[str] = Field(
        default=[
            "check_availability",
            "create_appointment",
            "cancel_appointment",
            "send_confirmation",
        ],
        description="Available tools for the agent",
    )

    # Validation thresholds
    require_confirmation: bool = Field(
        default=True,
        description="Require user confirmation before actions",
    )
    min_confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to proceed",
    )
