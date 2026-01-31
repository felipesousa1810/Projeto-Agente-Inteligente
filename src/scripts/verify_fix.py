"""Verification script for NLG Fix."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.nlg import get_response_generator


def verify_nlg():
    print("--- Testing ResponseGenerator Instantiation ---")
    try:
        gen = get_response_generator()
        print("[OK] ResponseGenerator instantiated successfully.")
        print(f"[OK] Agent created: {gen.agent}")
    except TypeError as e:
        print(f"[FAIL] TypeError during instantiation: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Other error: {e}")
        sys.exit(1)

    print("\n>>> VERIFICATION PASSED <<<")


if __name__ == "__main__":
    verify_nlg()
