"""
get_linkedin_token.py
---------------------
Helper script to obtain a LinkedIn OAuth 2.0 access token.

Steps:
1. Go to https://www.linkedin.com/developers/ and create an app.
2. Under "Products", request access to "Share on LinkedIn" and "Sign In with LinkedIn".
3. Add http://localhost:8001/callback as an "Authorized Redirect URL".
4. Copy your Client ID and Client Secret below or into .env.
5. Run: python get_linkedin_token.py
6. Authorize in the browser, then copy the access token into your .env file.
"""

import os
import json
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID") or input("Enter LinkedIn Client ID: ").strip()
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET") or input("Enter LinkedIn Client Secret: ").strip()

REDIRECT_URI = "http://localhost:8001/callback"
SCOPES = "openid profile email w_member_social"
STATE = secrets.token_urlsafe(16)

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authorization successful! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Error: no code received.</h2>")

    def log_message(self, format, *args):
        pass  # Silence default HTTP logs


def main():
    global auth_code

    auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&state={STATE}"
        f"&scope={urllib.parse.quote(SCOPES)}"
    )

    print("\nOpening LinkedIn authorization page in your browser...")
    print(f"If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8001), CallbackHandler)
    print("Waiting for authorization callback on http://localhost:8001/callback ...")
    server.handle_request()

    if not auth_code:
        print("ERROR: No authorization code received.")
        return

    # Exchange code for access token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    resp = requests.post(
        token_url,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    token_data = resp.json()
    access_token = token_data["access_token"]

    # Get the person URN via the OpenID Connect userinfo endpoint
    profile_resp = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    profile_resp.raise_for_status()
    person_id = profile_resp.json()["sub"]
    person_urn = f"urn:li:person:{person_id}"

    print("\n" + "=" * 60)
    print("SUCCESS! Add these to your .env file:")
    print("=" * 60)
    print(f"LINKEDIN_ACCESS_TOKEN={access_token}")
    print(f"LINKEDIN_PERSON_URN={person_urn}")
    print("=" * 60)

    # Optionally write directly to .env
    write = input("\nWrite these to .env automatically? [y/N]: ").strip().lower()
    if write == "y":
        env_path = ".env"
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()

        keys_to_set = {
            "LINKEDIN_ACCESS_TOKEN": access_token,
            "LINKEDIN_PERSON_URN": person_urn,
        }
        updated = set()
        new_lines = []
        for line in lines:
            key = line.split("=")[0].strip()
            if key in keys_to_set:
                new_lines.append(f"{key}={keys_to_set[key]}\n")
                updated.add(key)
            else:
                new_lines.append(line)

        for key, val in keys_to_set.items():
            if key not in updated:
                new_lines.append(f"{key}={val}\n")

        with open(env_path, "w") as f:
            f.writelines(new_lines)
        print(f".env updated at {os.path.abspath(env_path)}")


if __name__ == "__main__":
    main()
