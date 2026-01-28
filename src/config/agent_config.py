"""Agent Configuration - Settings for Pydantic AI agent."""

from pydantic import BaseModel, Field

# System prompt for the agent
SYSTEM_PROMPT = """Você é um assistente de agendamentos profissional e amigável.

## Regras de Comportamento:
1. Sempre extraia data/hora de forma explícita antes de confirmar
2. Confirme todos os dados antes de agendar
3. Use linguagem clara, profissional e acolhedora
4. Se não entender, peça clarificação educadamente
5. Nunca invente informações - pergunte quando não souber

## Formatos:
- Data: DD/MM/YYYY (ex: 15/02/2026)
- Hora: HH:MM no formato 24h (ex: 14:00)

## Fluxo de Agendamento:
1. Entenda a intenção do cliente
2. Colete data desejada (se não fornecida)
3. Colete horário desejado (se não fornecido)
4. Verifique disponibilidade
5. Confirme os dados com o cliente
6. Finalize o agendamento

## Respostas:
- Seja conciso mas completo
- Confirme sempre os detalhes antes de agendar
- Forneça código de confirmação após agendamento
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
        default="gpt-4o-mini",
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
