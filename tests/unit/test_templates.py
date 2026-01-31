"""Unit Tests - Templates."""

from src.core.templates import (
    FAQ_KNOWLEDGE,
    get_faq_answer,
)

# Testes para a base de conhecimento (FAQ)
# A classe TestTemplates foi removida pois os templates estáticos foram substituídos pelo Guardrails.


class TestFAQKnowledge:
    """Tests for FAQ knowledge base."""

    def test_all_common_topics_covered(self) -> None:
        """Test that common dental topics are covered."""
        topics = ["limpeza", "clareamento", "restauração", "implante", "canal"]

        for topic in topics:
            assert topic in FAQ_KNOWLEDGE, f"Missing FAQ topic: {topic}"

    def test_get_faq_answer_exact_match(self) -> None:
        """Test that exact topic match works."""
        answer = get_faq_answer("limpeza")

        assert "limpeza" in answer.lower() or "profilaxia" in answer.lower()
        assert "R$" in answer  # Should contain pricing

    def test_get_faq_answer_none_returns_default(self) -> None:
        """Test that None topic returns default answer."""
        answer = get_faq_answer(None)

        assert answer == FAQ_KNOWLEDGE["default"]

    def test_get_faq_answer_unknown_returns_default(self) -> None:
        """Test that unknown topic returns default."""
        answer = get_faq_answer("xyz_unknown_topic")

        assert answer == FAQ_KNOWLEDGE["default"]

    def test_get_faq_answer_partial_match(self) -> None:
        """Test that partial topic match works."""
        # "clarear" should match "clareamento"
        answer = get_faq_answer("clareamento dental")

        assert "clareamento" in answer.lower()
