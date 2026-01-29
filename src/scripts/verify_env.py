"""Verification Script - Check Environment & Connections."""

import asyncio
import os

from src.config.settings import get_settings
from src.services.supabase import get_supabase_client


async def verify_supabase():
    print("[INFO] Testing Supabase Connection...")
    try:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            print("   [ERROR] Missing SUPABASE_URL or SUPABASE_KEY")
            return False

        client = get_supabase_client()
        # Simple query to check connection (count customers)
        res = client.table("customers").select("count", count="exact").execute()
        print(f"   [SUCCESS] Connection successful! Found {res.count} customers.")
        return True
    except Exception as e:
        print(f"   [ERROR] Connection failed: {e}")
        return False


def verify_google_calendar():
    print("\n[INFO] Testing Google Calendar Credentials...")
    json_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not json_path:
        # Check for OAuth token (Dev/EasyPanel)
        if os.path.exists("token.json"):
            print("   [SUCCESS] Found 'token.json' (OAuth Local).")
            return True
        elif os.environ.get("GOOGLE_TOKEN_JSON"):
            print("   [SUCCESS] Found GOOGLE_TOKEN_JSON env var.")
            return True

        print("   [WARNING] GOOGLE_SERVICE_ACCOUNT_JSON env var not set.")
        print("   (Agent will use Mock or fail for Calendar operations)")
        return False

    print(f"   Found credential path: {json_path}")

    # Check if string content or file path
    if json_path.startswith("{"):
        print("   [SUCCESS] Detected JSON content directly in env var.")
        return True
    elif os.path.exists(json_path):
        print("   [SUCCESS] Detected valid file path.")
        return True
    else:
        print("   [ERROR] File path does not exist!")
        return False


async def main():
    print("[Start] Environment Verification...\n")

    sb_ok = await verify_supabase()
    gc_ok = verify_google_calendar()

    print("\n" + "=" * 30)
    if sb_ok and gc_ok:
        print("[System] ALL SYSTEMS READY!")
    elif sb_ok:
        print("[System] Supabase OK, but Calendar missing. Agent will work partially.")
    else:
        print("[System] Critical Config Missing.")


if __name__ == "__main__":
    asyncio.run(main())
