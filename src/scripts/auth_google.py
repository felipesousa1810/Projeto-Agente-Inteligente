"""Google OAuth Flow Script.

Run this script LOCALLY to authenticate with Google and generate 'token.json'.
This is required because you provided OAuth Client ID credentials, not a Service Account.
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

# Capabilities we need
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def authenticate():
    creds_file = "credentials.json"
    token_file = "token.json"

    if not os.path.exists(creds_file):
        print(f"❌ Error: '{creds_file}' not found.")
        return

    print("🚀 Starting Google Authentication...")
    print("   A browser window will open. Please login and grant access.")

    try:
        # Create the flow from the client secrets file
        flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)

        # Run the local server to receive the callback
        # Port 8080 is specified in your credentials.json redirect_uris
        creds = flow.run_local_server(port=8080)

        # Save the credentials for the next run
        with open(token_file, "w") as token:
            token.write(creds.to_json())

        print(f"✅ Authentication successful! Saved to '{token_file}'.")
        print("   The agent can now access Google Calendar.")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print(
            "\nNote: OAuth requires 'http://localhost' in your authorized redirect URIs."
        )
        print("Check your credentials.json content if creating the flow fails.")


if __name__ == "__main__":
    authenticate()
