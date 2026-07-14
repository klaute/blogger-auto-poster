#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests
import yaml


PLACEHOLDERS = {
    "BLOGGER_BLOG_ID",
    "GOOGLE_OAUTH_CLIENT_ID",
    "GOOGLE_OAUTH_CLIENT_SECRET",
    "GOOGLE_OAUTH_REFRESH_TOKEN",
}


def mask(value: str) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 10:
        return f"<len={len(value)}>"
    return f"{value[:4]}...{value[-6:]} (len={len(value)})"


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_client_secret(path: Path) -> tuple[str | None, str | None]:
    if not path.exists():
        return None, None
    data = json.loads(path.read_text(encoding="utf-8"))
    client = data.get("installed") or data.get("web") or {}
    return client.get("client_id"), client.get("client_secret")


def token_refresh(config: dict) -> tuple[bool, str]:
    blogger = config.get("blogger") or {}
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": blogger.get("client_id"),
            "client_secret": blogger.get("client_secret"),
            "refresh_token": blogger.get("refresh_token"),
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.ok:
        return True, "token refresh succeeded"
    return False, f"{response.status_code} {response.reason}: {payload}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yml")
    parser.add_argument("--credentials-file", default="credentials.json")
    parser.add_argument("--skip-network", action="store_true")
    args = parser.parse_args()

    config_path = Path(args.config)
    credentials_path = Path(args.credentials_file)
    if not config_path.exists():
        print(f"FAIL: config file missing: {config_path}")
        return 1

    config = load_yaml(config_path)
    blogger = config.get("blogger") or {}
    blog_id = str(blogger.get("blog_id") or "")
    client_id = str(blogger.get("client_id") or "")
    client_secret = str(blogger.get("client_secret") or "")
    refresh_token = str(blogger.get("refresh_token") or "")

    print("OAuth config diagnosis")
    print(f"config: {config_path}")
    print(f"credentials: {credentials_path}")
    print(f"blog_id: {mask(blog_id)}")
    print(f"client_id: {mask(client_id)}")
    print(f"client_secret: {mask(client_secret)}")
    print(f"refresh_token: {mask(refresh_token)}")

    problems: list[str] = []
    for key, value in {
        "blog_id": blog_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
    }.items():
        if not value:
            problems.append(f"missing blogger.{key}")
        if value in PLACEHOLDERS:
            problems.append(f"placeholder still set for blogger.{key}")

    if refresh_token.startswith("4/"):
        problems.append(
            "refresh_token looks like an OAuth authorization code, not a refresh token; "
            "do not paste the callback URL code into config.yml"
        )
    elif refresh_token and not refresh_token.startswith("1//"):
        problems.append("refresh_token does not start with expected '1//' prefix")
    if "\n" in refresh_token or "\r" in refresh_token or refresh_token.strip() != refresh_token:
        problems.append("refresh_token contains surrounding whitespace or newline")

    cred_client_id, cred_client_secret = load_client_secret(credentials_path)
    if cred_client_id is None:
        print("credentials.json: not found, skipping client match check")
    else:
        print(f"credentials client_id: {mask(str(cred_client_id))}")
        print(f"credentials client_secret: {mask(str(cred_client_secret or ''))}")
        if cred_client_id != client_id:
            problems.append("config blogger.client_id does not match credentials.json")
        if cred_client_secret != client_secret:
            problems.append("config blogger.client_secret does not match credentials.json")

    if problems:
        print("\nLocal problems:")
        for problem in problems:
            print(f"- {problem}")
        return 1

    print("\nLocal checks: OK")
    if args.skip_network:
        return 0

    ok, detail = token_refresh(config)
    if ok:
        print("Google token refresh: OK")
        return 0
    print(f"Google token refresh: FAILED: {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
