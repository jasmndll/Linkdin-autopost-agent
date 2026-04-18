import os
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
from config import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_SECRET,
    LINKEDIN_REDIRECT_URI
)

CONFIG_FILE = "config.py"
TOKEN_CACHE = "token_cache.json"

SCOPES = ["openid", "profile", "w_member_social"]

auth_code_holder = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            auth_code_holder["code"] = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2>Auth successful! You can close this tab.</h2>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h2>Auth failed. No code received.</h2>")

    def log_message(self, format, *args):
        pass  # suppress server logs


def get_authorization_url() -> str:
    params = {
        "response_type": "code",
        "client_id": LINKEDIN_CLIENT_ID,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "scope": " ".join(SCOPES),
        "state": "random_state_string"
    }
    base = "https://www.linkedin.com/oauth/v2/authorization"
    return f"{base}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": LINKEDIN_REDIRECT_URI,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET
    }
    response = requests.post(url, data=data)
    response.raise_for_status()
    return response.json()


def get_person_urn(access_token: str) -> str:
    url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    # sub field contains the person ID
    return f"urn:li:person:{data['sub']}"


def load_cached_token() -> dict | None:
    if os.path.exists(TOKEN_CACHE):
        with open(TOKEN_CACHE, "r") as f:
            return json.load(f)
    return None


def save_token_cache(token_data: dict, person_urn: str):
    with open(TOKEN_CACHE, "w") as f:
        json.dump({"access_token": token_data["access_token"], "person_urn": person_urn}, f)
    print("[✓] Token cached to token_cache.json")


def authenticate() -> tuple[str, str]:
    """Returns (access_token, person_urn). Uses cache if available."""

    cached = load_cached_token()
    if cached:
        print("[✓] Using cached LinkedIn token.")
        return cached["access_token"], cached["person_urn"]

    print("\n[*] Starting LinkedIn OAuth flow...")
    url = get_authorization_url()
    print(f"[*] Opening browser for authorization...")
    webbrowser.open(url)

    # Start local server to catch the callback
    server = HTTPServer(("localhost", 8000), CallbackHandler)
    print("[*] Waiting for LinkedIn callback on http://localhost:8000/callback ...")
    server.handle_request()

    if "code" not in auth_code_holder:
        raise Exception("Authorization failed. No code received.")

    print("[*] Exchanging code for access token...")
    token_data = exchange_code_for_token(auth_code_holder["code"])
    access_token = token_data["access_token"]

    print("[*] Fetching your LinkedIn profile URN...")
    person_urn = get_person_urn(access_token)

    save_token_cache(token_data, person_urn)
    print(f"[✓] Authenticated! Person URN: {person_urn}")

    return access_token, person_urn