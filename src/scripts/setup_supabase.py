"""Supabase Infrastructure Setup Script.

This script acts as an automated infrastructure agent to:
1. Create a Supabase Project (via Management API).
2. Configure Database Schema (via Direct Postgres Connection).

Requires:
- SUPABASE_ACCESS_TOKEN (Personal Access Token)
- Requests library
- Psycopg2 library
"""

import os
import time

import psycopg2
import requests

SUPABASE_API_URL = "https://api.supabase.com/v1"


def get_access_token():
    token = os.environ.get("SUPABASE_ACCESS_TOKEN")
    if not token:
        print("[ERROR] Error: SUPABASE_ACCESS_TOKEN env var not set.")
        print("Please generate one at: https://supabase.com/dashboard/account/tokens")
        return None
    return token


def get_organizations(headers):
    resp = requests.get(
        f"{SUPABASE_API_URL}/organizations", headers=headers, timeout=10
    )
    if resp.status_code != 200:
        print(f"[ERROR] Failed to list orgs: {resp.text}")
        return []
    return resp.json()


def create_project(headers, org_id, project_name, db_pass, region="us-east-1"):
    payload = {
        "organization_id": org_id,
        "name": project_name,
        "db_pass": db_pass,
        "region": region,
        "plan": "free",
    }
    print(f"[INFO] Creating project '{project_name}' in org {org_id}...")
    resp = requests.post(
        f"{SUPABASE_API_URL}/projects", json=payload, headers=headers, timeout=10
    )

    if resp.status_code == 201:
        return resp.json()
    else:
        print(f"[ERROR] Failed to create project: {resp.text}")
        return None


def wait_for_active(headers, project_ref):
    print("[INFO] Waiting for project to be ACTIVE (this may take 2-3 mins)...")
    while True:
        resp = requests.get(
            f"{SUPABASE_API_URL}/projects/{project_ref}", headers=headers, timeout=10
        )
        if resp.status_code == 200:
            status = resp.json().get("status")
            print(f"   Status: {status}")
            if status == "ACTIVE_HEALTHY":
                return resp.json()
        else:
            print(f"   Check failed: {resp.status_code}")

        time.sleep(10)


def apply_schema(connection_string, schema_path):
    print("[INFO] Applying database schema...")
    try:
        conn = psycopg2.connect(connection_string)
        cur = conn.cursor()

        with open(schema_path, encoding="utf-8") as f:
            sql = f.read()
            cur.execute(sql)

        conn.commit()
        cur.close()
        conn.close()
        print("[SUCCESS] Schema applied successfully!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to apply schema: {e}")
        return False


def list_projects(headers):
    resp = requests.get(f"{SUPABASE_API_URL}/projects", headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"[ERROR] Failed to list projects: {resp.text}")
        return []
    return resp.json()


def main():
    token = get_access_token()
    if not token:
        return

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    print("[INFO] Fetching projects...")
    projects = list_projects(headers)

    selected_project = None

    if projects:
        print("\n[INFO] Existing Projects:")
        for idx, proj in enumerate(projects):
            print(
                f"{idx + 1}. {proj['name']} (ID: {proj['id']}, Status: {proj['status']})"
            )
        print(f"{len(projects) + 1}. [Create New Project]")

        try:
            selection = int(input("\nSelect project (1-N): ") or 1) - 1
            if selection < len(projects):
                selected_project = projects[selection]
        except ValueError:
            pass

    if not selected_project:
        # Create New Flow
        # 1. Select Org
        orgs = get_organizations(headers)
        if not orgs:
            return

        print("\nSelect Organization:")
        for idx, org in enumerate(orgs):
            print(f"{idx + 1}. {org['name']} ({org['id']})")

        try:
            selection = int(input("Enter number (default 1): ") or 1) - 1
            org_id = orgs[selection]["id"]
        except Exception:
            org_id = orgs[0]["id"]

        # 2. Project Details
        project_name = input("Project Name (default: Agent-Prod): ") or "Agent-Prod"
        db_pass = input("Database Password (min 12 chars): ")
        if len(db_pass) < 6:
            print("[ERROR] Password too short.")
            return

        # 3. Create
        project_data = create_project(headers, org_id, project_name, db_pass)
        if not project_data:
            return
        selected_project = project_data

        # 4. Wait for Ready
        selected_project = wait_for_active(headers, selected_project["id"])
    else:
        # Existing Project Flow
        print(f"\n[INFO] Selected '{selected_project['name']}'")
        db_pass = input("Enter Database Password (to connect via SQL): ")

    project_ref = selected_project["id"]

    # 5. Connection String
    # Construct postgres connection string
    # postgres://postgres:[password]@db.[ref].supabase.co:5432/postgres
    # Host is usually db.ref.supabase.co
    db_host = f"db.{project_ref}.supabase.co"
    connection_string = f"postgres://postgres:{db_pass}@{db_host}:5432/postgres"

    print("\n[INFO] Connection Info:")
    print(f"URL: https://{project_ref}.supabase.co")
    print(f"DB String: postgres://postgres:****@{db_host}:5432/postgres")

    # 6. Apply Schema
    schema_path = os.path.join("src", "db", "schema.sql")
    if os.path.exists(schema_path):
        apply_schema(connection_string, schema_path)
    else:
        print(f"[WARNING] Schema file not found at {schema_path}")

    print("\n[INFO] NEXT STEPS:")
    print("1. Update your .env file with:")
    print(f"   SUPABASE_URL=https://{project_ref}.supabase.co")
    print("   SUPABASE_KEY=<your_anon_key_from_dashboard>")


if __name__ == "__main__":
    main()
