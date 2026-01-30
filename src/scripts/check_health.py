import asyncio
import os

from dotenv import load_dotenv

from supabase import Client, create_client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in environment.")
    exit(1)


async def check_health():
    print(f"Connecting to Supabase at {SUPABASE_URL}...")
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # 1. Check connection by selecting a simple table or calling a function
        # We'll try to count items in 'customers' or just check if we can query
        print("1. Testing Database Connection...")
        try:
            response = (
                supabase.table("customers")
                .select("*", count="exact")
                .limit(1)
                .execute()
            )
            print(f"[OK] Connection Successful. Customer count: {response.count}")
        except Exception as e:
            print(f"[ERROR] Database Connection Failed: {e}")
            return

        # 2. Check Dead Letter Queue
        print("\n2. Checking Dead Letter Queue (last 24h)...")
        try:
            dlq_response = (
                supabase.table("dead_letter_queue")
                .select("*")
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            if dlq_response.data:
                print(f"[WARN] Found {len(dlq_response.data)} recent errors in DLQ:")
                for error in dlq_response.data:
                    print(
                        f"   - [{error.get('created_at')}] {error.get('error_type')}: {error.get('error_message')}"
                    )
            else:
                print("[OK] DLQ is empty (Last 5 checks).")
        except Exception as e:
            print(f"[ERROR] Failed to check DLQ: {e}")

        # 3. Check Messages
        print("\n3. Checking Recent Messages (last 5)...")
        try:
            msgs_response = (
                supabase.table("messages")
                .select("*")
                .order("processed_at", desc=True)
                .limit(5)
                .execute()
            )
            if msgs_response.data:
                for msg in msgs_response.data:
                    print(
                        f"   - [{msg.get('processed_at')}] {msg.get('direction')} | {msg.get('intent')} | {msg.get('body')}"
                    )
            else:
                print("[INFO] No recent messages found.")
        except Exception as e:
            print(f"[ERROR] Failed to check messages: {e}")

    except Exception as e:
        print(f"[CRITICAL] Critical Error: {e}")


if __name__ == "__main__":
    asyncio.run(check_health())
