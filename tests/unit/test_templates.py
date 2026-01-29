"""Unit Tests - Templates."""

from src.core.templates import (
    FAQ_KNOWLEDGE,
    TEMPLATES,
    format_template,
    get_faq_answer,
    get_template,
)


class TestTemplates:
    """Tests for response templates."""

    def test_all_required_templates_exist(self) -> None:
        """Test that all required template keys exist."""
        required_keys = [
            "greeting",
            "ask_procedure",
            "ask_date",
            "ask_time",
            "confirm_appointment",
            "appointment_confirmed",
            "clarify",
            "error",
        ]

        for key in required_keys:
            assert key in TEMPLATES, f"Missing template: {key}"

    def test_get_template_returns_correct_template(self) -> None:
        """Test that get_template returns the right template."""
        template = get_template("greeting")

        assert "OdontoSorriso" in template
        assert "👋" in template

    def test_get_template_returns_error_for_unknown(self) -> None:
        """Test that unknown key returns error template."""
        template = get_template("nonexistent_key")

        assert template == TEMPLATES["error"]

    def test_format_template_fills_placeholders(self) -> None:
        """Test that format_template fills placeholders correctly."""
        result = format_template(
            "confirm_appointment",
            procedure="Limpeza",
            date="15/02/2026",
            time="14:00",
        )

        assert "Limpeza" in result
        assert "15/02/2026" in result
        assert "14:00" in result

    def test_format_template_missing_key_returns_template(self) -> None:
        """Test that missing placeholder key doesn't crash."""
        # Should not raise, just return template as-is
        result = format_template("ask_date")  # Missing 'procedure'

        assert result is not None

    def test_confirm_appointment_template_has_all_fields(self) -> None:
        """Test that confirm template includes all required fields."""
        template = TEMPLATES["confirm_appointment"]

        assert "{procedure}" in template
        assert "{date}" in template
        assert "{time}" in template


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
