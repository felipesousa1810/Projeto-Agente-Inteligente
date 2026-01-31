"""Knowledge Management Module.

Handles loading and serving the knowledge base content to the agent.
Uses LRU cache to avoid unnecessary I/O operations.
"""

from functools import lru_cache
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


@lru_cache
def load_knowledge_base() -> str:
    """Load the knowledge base from docs/FAQ.md.

    Returns:
        The content of the FAQ.md file as a string.
        Returns an empty string if the file is not found.
    """
    try:
        # Assuming docs/FAQ.md is in the project root relative to execution
        # Or relative to this file? Let's use absolute path relative to project root
        project_root = Path(__file__).parent.parent.parent
        faq_path = project_root / "docs" / "FAQ.md"

        if not faq_path.exists():
            logger.warning("knowledge_base_not_found", path=str(faq_path))
            return ""

        content = faq_path.read_text(encoding="utf-8")
        logger.info("knowledge_base_loaded", size_bytes=len(content))
        return content

    except Exception as e:
        logger.error("knowledge_base_load_error", error=str(e))
        return ""
