"""Knowledge Base for the Agent.

This module contains static knowledge used by the agent, such as FAQ answers.
Legacy templates have been removed in favor of PydanticAI Guardrails (`src/core/guardrails.py`).
"""

# FAQ Knowledge Base (DEPRECATED - Moved to docs/FAQ.md via Context Injection)
FAQ_KNOWLEDGE: dict[str, str] = {}


def get_faq_answer(topic: str | None) -> str:
    """Get FAQ answer for a topic.

    DEPRECATED: Use Context Injection logic instead.
    """
    return "Consulte a equipe de atendimento."
