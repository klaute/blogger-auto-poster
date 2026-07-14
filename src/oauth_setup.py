from __future__ import annotations

import argparse
import json
import http.server
import socketserver
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path

import requests
import yaml


SCOPE = "https://www.googleapis.com/auth/blogger"


@dataclass
class CallbackState:
    code: str | None = None
    error: str | None = None


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    state: CallbackState

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.state.code = (params.get("code") or [None])[0]
        self.state.error = (params.get("error") or [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        if self.state.code:
            self.wfile.write(b"Authorization received. You can close this browser tab.\n")
        else:
            message = f"Authorization failed: {self.state.error or 'missing code'}\n"
            self.wfile.write(message.encode("utf-8"))

    def log_message(self, format: str, *args: object) -> None:
        return


def build_auth_url(client_id: str, redirect_uri: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)


def exchange_code(client_id: str, client_secret: str, redirect_uri: str, code: str) -> dict:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def extract_code(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urllib.parse.urlparse(value)
        params = urllib.parse.parse_qs(parsed.query)
        return (params.get("code") or [None])[0]
    return value


def read_client_secrets(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    client_data = data.get("installed") or data.get("web")
    if not isinstance(client_data, dict):
        raise ValueError("credentials.json must contain an 'installed' or 'web' client.")
    client_id = client_data.get("client_id")
    client_secret = client_data.get("client_secret")
    if not client_id or not client_secret:
        raise ValueError("credentials.json does not contain client_id/client_secret.")
    return str(client_id), str(client_secret)


def update_config(path: Path, client_id: str, client_secret: str, refresh_token: str) -> None:
    config = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(config, dict):
        config = {}
    blogger = config.setdefault("blogger", {})
    if not isinstance(blogger, dict):
        blogger = {}
        config["blogger"] = blogger
    blogger["client_id"] = client_id
    blogger["client_secret"] = client_secret
    blogger["refresh_token"] = refresh_token
    path.write_text(yaml.safe_dump(config, allow_unicode=False, sort_keys=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a Blogger OAuth refresh token.")
    parser.add_argument("--client-id")
    parser.add_argument("--client-secret")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--update-config")
    parser.add_argument(
        "--manual-code",
        action="store_true",
        help="Do not start a callback server; paste the callback URL or code manually.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)

    if args.client_id and args.client_secret:
        client_id = args.client_id
        client_secret = args.client_secret
    else:
        client_id, client_secret = read_client_secrets(Path(args.credentials_file))

    redirect_uri = f"http://{args.host}:{args.port}/callback"
    auth_url = build_auth_url(client_id, redirect_uri)
    if args.manual_code:
        print("Open this URL in a browser and approve Blogger access:\n")
        print(auth_url)
        print("\nAfter Google redirects to a local callback URL, copy the full URL.")
        print("Paste the full callback URL or only the code= value below.")
        code = extract_code(input("\nCallback URL or code: ").strip())
        if not code:
            print("OAuth failed: no code was provided.", file=sys.stderr)
            return 1
    else:
        state = CallbackState()

        handler = type("Handler", (OAuthCallbackHandler,), {"state": state})
        with socketserver.TCPServer((args.host, args.port), handler) as server:
            print("Open this URL in a browser and approve Blogger access:\n")
            print(auth_url)
            print(
                "\nIf this runs on a remote server, open an SSH tunnel first, for example:"
            )
            print(f"ssh -L {args.port}:127.0.0.1:{args.port} USER@SERVER")
            print("\nWaiting for OAuth callback...")
            server.handle_request()

        if state.error:
            print(f"OAuth failed: {state.error}", file=sys.stderr)
            return 1
        if not state.code:
            print("OAuth failed: callback did not contain a code.", file=sys.stderr)
            return 1
        code = state.code

    try:
        token_data = exchange_code(client_id, client_secret, redirect_uri, code)
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        print(f"OAuth token exchange failed: {detail}", file=sys.stderr)
        return 1
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        print("No refresh_token returned. Re-run with consent or revoke the old app grant.", file=sys.stderr)
        return 1

    if args.update_config:
        update_config(Path(args.update_config), client_id, client_secret, refresh_token)
        print(f"\nUpdated {args.update_config} with client_id, client_secret and refresh_token.")
    else:
        print("\nAdd these values to config/config.yml:")
        print(f"blogger.client_id: {client_id}")
        print("blogger.client_secret: <from credentials.json>")
        print(f"blogger.refresh_token: {refresh_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
