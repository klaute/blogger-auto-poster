from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

LOGGER = logging.getLogger("blogger-auto-poster")


def pushover_endpoint(pushover_config: dict[str, Any]) -> str:
    host = str(pushover_config.get("host") or "").strip()
    if host:
        try:
            port = int(pushover_config.get("port") or 8090)
        except (TypeError, ValueError):
            port = 8090
        return f"http://{host}:{port}/send"

    configured_url = str(pushover_config.get("url") or "").strip()
    if configured_url:
        return normalize_pushover_url(configured_url)

    try:
        port = int(pushover_config.get("port") or 8090)
    except (TypeError, ValueError):
        port = 8090
    return f"http://localhost:{port}/send"


def normalize_pushover_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme in {"http", "https"} and parsed.port == 5000:
        host = parsed.hostname or ""
        netloc = f"{host}:8090"
        if parsed.username:
            credentials = parsed.username
            if parsed.password:
                credentials = f"{credentials}:{parsed.password}"
            netloc = f"{credentials}@{netloc}"
        return urlunparse(parsed._replace(netloc=netloc))
    return url


def pushover_mode(pushover_config: dict[str, Any]) -> str:
    mode = str(pushover_config.get("mode") or "get").strip().lower()
    return "post" if mode == "post" else "get"


def pushover_dedupe_key(config: dict[str, Any], event: str, identifier: str) -> str:
    pushover_config = (config.get("notifications") or {}).get("pushover") or {}
    prefix = str(pushover_config.get("dedupe_prefix") or "blogger-auto-poster").strip()
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}:{event}:{digest}"


def send_pushover_message(
    config: dict[str, Any],
    message: str,
    title: str | None = None,
    dedupe_key: str | None = None,
) -> tuple[bool, str | None]:
    pushover_config = (config.get("notifications") or {}).get("pushover") or {}
    if not bool(pushover_config.get("enabled", False)):
        return True, None

    url = pushover_endpoint(pushover_config)
    token = str(pushover_config.get("token") or "").strip()
    app_name = str(title or pushover_config.get("app_name") or "Blogger Auto Poster").strip()
    mode = pushover_mode(pushover_config)
    try:
        timeout_seconds = int(pushover_config.get("timeout_seconds", 10))
    except (TypeError, ValueError):
        timeout_seconds = 10
    if not url or not token:
        return False, "Pushover notification is enabled but endpoint or token is missing."

    try:
        if mode == "post":
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            if dedupe_key:
                headers["Idempotency-Key"] = dedupe_key
            response = requests.post(
                url,
                headers=headers,
                json={
                    "title": app_name,
                    "message": message,
                    "provider": "pushover",
                },
                timeout=timeout_seconds,
            )
        else:
            params = {
                "token": token,
                "title": app_name,
                "message": message,
            }
            if dedupe_key:
                params["dedupe_key"] = dedupe_key
            response = requests.get(url, params=params, timeout=timeout_seconds)
        response.raise_for_status()
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_pushover_upload_notification(
    config: dict[str, Any],
    title: str,
    source_name: str,
    publish_mode: str,
    labels: list[str],
) -> None:
    message = (
        f"Starting Blogger {publish_mode} upload: {title} "
        f"({source_name}); labels: {', '.join(labels)}"
    )
    dedupe_key = pushover_dedupe_key(config, "upload-start", f"{publish_mode}:{source_name}:{title}")
    ok, error = send_pushover_message(config, message, dedupe_key=dedupe_key)
    if not ok:
        LOGGER.warning("Pushover notification failed: %s", error)


def compact_error(exc: Exception, max_length: int = 500) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def send_pushover_error_notification(
    config: dict[str, Any],
    summary: str,
    exc: Exception,
    next_action: str,
) -> None:
    message = (
        f"{summary}\n"
        f"Error: {compact_error(exc)}\n"
        f"Next: {next_action}"
    )
    dedupe_key = pushover_dedupe_key(config, "error", f"{summary}:{compact_error(exc)}")
    ok, error = send_pushover_message(config, message, dedupe_key=dedupe_key)
    if not ok:
        LOGGER.warning("Pushover error notification failed: %s", error)


def verify_pushover_report(config: dict[str, Any]) -> dict[str, Any]:
    pushover_config = (config.get("notifications") or {}).get("pushover") or {}
    enabled = bool(pushover_config.get("enabled", False))
    title = str(pushover_config.get("app_name") or "Blogger Auto Poster").strip()
    message = f"Blogger Auto Poster verification {datetime.now(timezone.utc).isoformat()}"
    endpoint = pushover_endpoint(pushover_config)
    mode = pushover_mode(pushover_config)
    dedupe_key = pushover_dedupe_key(config, "verification", title)
    if not enabled:
        return {
            "ok": True,
            "skipped": True,
            "enabled": False,
            "endpoint": endpoint,
            "mode": mode,
            "message": "Pushover notification is disabled in config.",
        }

    ok, error = send_pushover_message(
        config,
        message,
        title=title,
        dedupe_key=dedupe_key,
    )
    return {
        "ok": ok,
        "skipped": False,
        "enabled": True,
        "endpoint": endpoint,
        "mode": mode,
        "title": title,
        "dedupe_key": dedupe_key,
        "error": error,
    }
