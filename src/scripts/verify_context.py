"""Verification script for Context Injection."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.config.agent_config import get_dynamic_system_prompt  # noqa: E402
from src.core.knowledge import load_knowledge_base  # noqa: E402


def verify_context_injection():
    print("--- 1. Testing Knowledge Load ---")
    kb = load_knowledge_base()
    if not kb:
        print("❌ Failed to load knowledge base!")
        sys.exit(1)

    print(f"[OK] Knowledge loaded. Size: {len(kb)} chars")
    # print(f"Preview: {kb[:100]}...")

    print("\n--- 2. Testing System Prompt Injection ---")
    prompt = get_dynamic_system_prompt()

    if kb in prompt:
        print("[OK] SUCCESS: Knowledge base FOUND in system prompt.")
    else:
        print("[FAIL] FAILURE: Knowledge base NOT found in system prompt.")
        sys.exit(1)

    print("\n--- 3. Prompt Structure Check ---")
    if "### Base de Conhecimento" in prompt:
        print("[OK] Section '### Base de Conhecimento' found.")
    else:
        print("[FAIL] Section '### Base de Conhecimento' missing.")

    print("\n>>> ALL CHECKS PASSED <<<")


if __name__ == "__main__":
    verify_context_injection()
