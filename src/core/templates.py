"""Response Templates - Base templates for all agent responses.

Templates are the "skeleton" of responses. They contain:
- Fixed structure and required information
- Placeholders for dynamic data
- Emojis and tone markers

The NLG module humanizes these templates without changing the data.
"""

from typing import Any

# Response templates organized by action type
TEMPLATES: dict[str, str] = {
    # Greetings
    "greeting": (
        "Olá! 👋 Sou o assistente virtual da OdontoSorriso. "
        "Como posso ajudar você hoje? Posso agendar consultas, "
        "responder dúvidas sobre tratamentos, ou ajudar com seu agendamento."
    ),
    "denied_restart": (
        "Sem problemas! 😊 Se precisar de algo, é só me chamar. "
        "Como posso ajudar você?"
    ),
    # Scheduling flow
    "ask_procedure": (
        "Qual procedimento você gostaria de agendar? 🦷\n\n"
        "Temos:\n"
        "• Limpeza\n"
        "• Clareamento\n"
        "• Restauração\n"
        "• Avaliação geral\n"
        "• Outros tratamentos"
    ),
    "ask_date": (
        "Ótimo! {procedure} é um excelente procedimento. 📅\n\n"
        "Para qual data você gostaria de agendar?"
    ),
    "ask_time": (
        "Perfeito! Para o dia {date}, temos os seguintes horários disponíveis:\n\n"
        "{available_slots}\n\n"
        "Qual horário você prefere?"
    ),
    "ask_time_no_slots": (
        "Infelizmente não temos horários disponíveis para o dia {date}. 😔\n\n"
        "Posso sugerir outra data?"
    ),
    "confirm_appointment": (
        "📋 Confirmando agendamento:\n\n"
        "• Procedimento: {procedure}\n"
        "• Data: {date}\n"
        "• Horário: {time}\n\n"
        "Confirma o agendamento? (sim/não)"
    ),
    "appointment_confirmed": (
        "✅ Agendamento confirmado!\n\n"
        "• Procedimento: {procedure}\n"
        "• Data: {date}\n"
        "• Horário: {time}\n"
        "• Código: {confirmation_code}\n\n"
        "Guarde este código para futuras referências. "
        "Enviaremos um lembrete um dia antes da consulta!"
    ),
    "appointment_already_confirmed": (
        "Seu agendamento já está confirmado! ✅\n"
        "Se precisar alterar ou cancelar, é só me avisar."
    ),
    # Cancellation flow
    "ask_confirmation_code": (
        "Para cancelar seu agendamento, por favor informe o código de confirmação. 📝\n\n"
        "O código foi enviado quando você agendou (formato: APPT-XXXXXXXX)."
    ),
    "cancel_appointment": (
        "✅ Agendamento {confirmation_code} cancelado com sucesso.\n\n"
        "Se precisar reagendar, é só me avisar!"
    ),
    "cancel_not_found": (
        "❌ Não encontrei nenhum agendamento com o código {confirmation_code}.\n\n"
        "Verifique o código e tente novamente. "
        "Se precisar de ajuda, é só me chamar!"
    ),
    # FAQ responses
    "faq_response": (
        "Sobre {procedure}:\n\n{answer}\n\n" "Posso ajudar com mais alguma coisa?"
    ),
    "faq_generic": ("{answer}\n\n" "Posso ajudar com algo mais?"),
    # Clarification
    "clarify": (
        "Desculpe, não entendi bem. 🤔\n\n"
        "Você pode:\n"
        "• Agendar uma consulta\n"
        "• Cancelar um agendamento\n"
        "• Tirar dúvidas sobre tratamentos\n\n"
        "Como posso ajudar?"
    ),
    "clarify_confirm": (
        "Não tenho certeza do que você está confirmando. 🤔\n\n"
        "Gostaria de agendar uma consulta?"
    ),
    # Error handling
    "error": (
        "Desculpe, ocorreu um erro ao processar sua mensagem. 😔\n\n"
        "Por favor, tente novamente em alguns instantes."
    ),
}


# FAQ knowledge base for common questions
FAQ_KNOWLEDGE: dict[str, str] = {
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


def get_template(template_key: str) -> str:
    """Get a template by its key.

    Args:
        template_key: Key of the template to retrieve.

    Returns:
        Template string, or error template if not found.
    """
    return TEMPLATES.get(template_key, TEMPLATES["error"])


def format_template(template_key: str, **context: Any) -> str:
    """Format a template with context data.

    Args:
        template_key: Key of the template.
        **context: Data to fill placeholders.

    Returns:
        Formatted template string.
    """
    template = get_template(template_key)
    try:
        return template.format(**context)
    except KeyError:
        # Missing placeholder - return template as-is
        return template


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
