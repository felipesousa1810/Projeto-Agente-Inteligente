"""Unit tests for knowledge module."""

from pathlib import Path
from unittest.mock import patch

from src.core.knowledge import load_knowledge_base


def test_load_knowledge_base_success() -> None:
    """Test loading knowledge base successfully."""
    mock_content = "# Test Knowledge"

    with (
        patch.object(Path, "exists", return_value=True),
        patch.object(Path, "read_text", return_value=mock_content),
    ):
        # Clear cache to ensure fresh load
        load_knowledge_base.cache_clear()
        content = load_knowledge_base()

        assert content == mock_content


def test_load_knowledge_base_not_found() -> None:
    """Test handling when file does not exist."""
    with patch.object(Path, "exists", return_value=False):
        load_knowledge_base.cache_clear()
        content = load_knowledge_base()

        assert content == ""


def test_load_knowledge_base_integration() -> None:
    """Integration test: real file load."""
    load_knowledge_base.cache_clear()
    content = load_knowledge_base()

    # Should load the real file we created
    assert "# Base de Conhecimento - OdontoSorriso" in content
    assert "Limpeza (Profilaxia)" in content
