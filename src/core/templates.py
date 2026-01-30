"""Knowledge Base for the Agent.

This module contains static knowledge used by the agent, such as FAQ answers.
Legacy templates have been removed in favor of PydanticAI Guardrails (`src/core/guardrails.py`).
"""

# FAQ Knowledge Base (formerly FAQ_KNOWLEDGE)
FAQ_KNOWLEDGE = {
    "limpeza": (
        "A limpeza dental (profilaxia) remove tártaro e placa bacteriana. "
        "O procedimento dura cerca de 30-40 minutos e é recomendado a cada 6 meses. "
        "Valor: a partir de R$ 150."
    ),
    "clareamento": (
        "O clareamento dental pode ser feito em consultório (1-2 sessões) "
        "ou com moldeira caseira (2-3 semanas). "
        "Resultados visíveis de 2-4 tons mais claros. "
        "Valor: a partir de R$ 500."
    ),
    "restauração": (
        "A restauração repara dentes danificados por cáries ou fraturas. "
        "Usamos resina da cor do dente para resultado natural. "
        "Procedimento indolor com anestesia local. "
        "Valor: a partir de R$ 200."
    ),
    "implante": (
        "O implante dental substitui dentes perdidos com um pino de titânio. "
        "O processo completo leva 3-6 meses. "
        "Durabilidade: pode durar toda a vida com cuidados adequados. "
        "Avaliação necessária para orçamento."
    ),
    "canal": (
        "O tratamento de canal remove a polpa infectada do dente. "
        "Salva o dente de extração. Normalmente 1-2 sessões. "
        "Procedimento indolor com anestesia. "
        "Valor: a partir de R$ 400."
    ),
    "ortodontia": (
        "Oferecemos ortodontia tradicional (aparelho metálico) "
        "e alinhadores invisíveis. Tratamento de 12-24 meses. "
        "Consulta de avaliação gratuita para orçamento personalizado."
    ),
    "horario": (
        "Funcionamos de segunda a sexta, das 8h às 18h. "
        "Sábados das 8h às 12h. Fechados aos domingos."
    ),
    "endereco": (
        "Estamos localizados na Av. Principal, 1000 - Centro. "
        "Próximo ao Shopping Center. Estacionamento gratuito para pacientes."
    ),
    "default": (
        "Oferecemos diversos tratamentos odontológicos com profissionais qualificados. "
        "Para mais informações sobre procedimentos específicos ou valores, "
        "agende uma avaliação gratuita!"
    ),
}


def get_faq_answer(topic: str | None) -> str:
    """Get FAQ answer for a topic.

    Args:
        topic: Topic to look up.

    Returns:
        Answer string.
    """
    if not topic:
        return FAQ_KNOWLEDGE["default"]

    topic_lower = topic.lower()

    # Direct match
    if topic_lower in FAQ_KNOWLEDGE:
        return FAQ_KNOWLEDGE[topic_lower]

    # Partial match
    for key, answer in FAQ_KNOWLEDGE.items():
        if key in topic_lower or topic_lower in key:
            return answer

    return FAQ_KNOWLEDGE["default"]
