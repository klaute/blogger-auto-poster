from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from src.markdown_posts import PostDocument
from src.notifications import send_pushover_error_notification, send_pushover_upload_notification
from src.scheduling import blogger_datetime

LOGGER = logging.getLogger("blogger-auto-poster")


def response_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return f"{response.status_code} {response.reason}: {payload}"


def refresh_access_token(blogger_config: dict[str, Any]) -> str:
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": blogger_config["client_id"],
            "client_secret": blogger_config["client_secret"],
            "refresh_token": blogger_config["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(f"OAuth token refresh failed: {response_error_detail(response)}")
    token_data = response.json()
    return token_data["access_token"]


def insert_post(
    config: dict[str, Any],
    post: PostDocument,
    html: str,
    labels: list[str],
    scheduled_datetime: datetime | None = None,
) -> dict[str, Any]:
    blogger_config = config["blogger"]
    posting_config = config.get("posting", {})
    publish_mode = str(posting_config.get("publish_mode", "draft")).lower()
    is_draft = publish_mode == "draft"
    payload = {
        "kind": "blogger#post",
        "title": post.title,
        "content": html,
        "labels": labels,
    }
    published = blogger_datetime(scheduled_datetime)
    if published:
        payload["published"] = published
    send_pushover_upload_notification(config, post.title, post.path.name, publish_mode, labels)
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
        params={"isDraft": str(is_draft).lower()},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def update_post(
    config: dict[str, Any],
    post_id: str,
    post: PostDocument,
    html: str,
    labels: list[str],
    scheduled_datetime: datetime | None = None,
) -> dict[str, Any]:
    blogger_config = config["blogger"]
    payload = {
        "kind": "blogger#post",
        "title": post.title,
        "content": html,
        "labels": labels,
    }
    published = blogger_datetime(scheduled_datetime)
    if published:
        payload["published"] = published
    send_pushover_upload_notification(config, post.title, post.path.name, "update", labels)
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.patch(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def insert_draft_post(
    config: dict[str, Any],
    title: str,
    html: str,
    labels: list[str],
) -> dict[str, Any]:
    blogger_config = config["blogger"]
    send_pushover_upload_notification(config, title, "verification-draft", "draft", labels)
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
        params={"isDraft": "true"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "kind": "blogger#post",
            "title": title,
            "content": html,
            "labels": labels,
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def delete_post(config: dict[str, Any], post_id: str) -> None:
    blogger_config = config["blogger"]
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.delete(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()


def get_post(config: dict[str, Any], post_id: str) -> dict[str, Any]:
    blogger_config = config["blogger"]
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.get(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}",
        params={"view": "ADMIN", "fetchBodies": "false"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def publish_post(config: dict[str, Any], post_id: str) -> dict[str, Any]:
    blogger_config = config["blogger"]
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}/publish",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def revert_post(config: dict[str, Any], post_id: str) -> dict[str, Any]:
    blogger_config = config["blogger"]
    access_token = refresh_access_token(blogger_config)
    blog_id = blogger_config["blog_id"]
    response = requests.post(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts/{post_id}/revert",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def list_blogger_posts(
    config: dict[str, Any],
    access_token: str,
    status: str,
    page_token: str | None = None,
) -> dict[str, Any]:
    blogger_config = config["blogger"]
    blog_id = blogger_config["blog_id"]
    params = {
        "status": status,
        "view": "ADMIN",
        "fetchBodies": "true",
        "maxResults": "50",
    }
    if page_token:
        params["pageToken"] = page_token
    response = requests.get(
        f"https://www.googleapis.com/blogger/v3/blogs/{blog_id}/posts",
        params=params,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def find_remote_post_by_marker(config: dict[str, Any], marker: str) -> dict[str, Any] | None:
    tracking_config = config.get("tracking") or {}
    if not bool(tracking_config.get("remote_check_enabled", True)):
        return None
    statuses = tracking_config.get("remote_statuses") or ["draft", "live", "scheduled"]
    max_pages = int(tracking_config.get("remote_max_pages_per_status", 10))
    access_token = refresh_access_token(config["blogger"])

    for status in statuses:
        page_token = None
        for _ in range(max_pages):
            data = list_blogger_posts(config, access_token, str(status), page_token)
            for item in data.get("items") or []:
                if marker in str(item.get("content") or ""):
                    return item
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return None


def list_existing_labels(config: dict[str, Any]) -> list[str]:
    tracking_config = config.get("tracking") or {}
    statuses = tracking_config.get("remote_statuses") or ["draft", "live", "scheduled"]
    max_pages = int(tracking_config.get("remote_max_pages_per_status", 10))
    access_token = refresh_access_token(config["blogger"])
    labels: set[str] = set()

    for status in statuses:
        page_token = None
        for _ in range(max_pages):
            data = list_blogger_posts(config, access_token, str(status), page_token)
            for item in data.get("items") or []:
                for label in item.get("labels") or []:
                    normalized = str(label).strip()
                    if normalized:
                        labels.add(normalized)
            page_token = data.get("nextPageToken")
            if not page_token:
                break
    return sorted(labels, key=str.casefold)


def verify_blogger_draft_cycle(config: dict[str, Any]) -> bool:
    created_post: dict[str, Any] | None = None
    title = f"Blogger Auto Poster Verification {datetime.now(timezone.utc).isoformat()}"
    labels = ["Blogger", "Verification", "Auto Poster"]
    html = (
        "<p>This temporary draft verifies Blogger API write and delete access. "
        "It should be deleted by the verification command.</p>"
    )
    try:
        created_post = insert_draft_post(config, title=title, html=html, labels=labels)
        post_id = created_post.get("id")
        status = created_post.get("status")
        if not post_id:
            raise RuntimeError("Blogger API response did not contain a post id.")
        if status and str(status).upper() != "DRAFT":
            raise RuntimeError(f"Verification post was not created as draft: status={status}")
        delete_post(config, post_id)
        LOGGER.info("Created and deleted Blogger verification draft %s", post_id)
        return True
    except Exception as exc:
        if created_post and created_post.get("id"):
            LOGGER.error(
                "Verification draft %s may still exist and should be deleted manually.",
                created_post.get("id"),
            )
        send_pushover_error_notification(
            config,
            "Blogger verification draft failed.",
            exc,
            "Check the command output and Blogger drafts for possible cleanup.",
        )
        raise


def verify_blogger_draft_cycle_report(config: dict[str, Any]) -> dict[str, Any]:
    created_post: dict[str, Any] | None = None
    title = f"Blogger Auto Poster Verification {datetime.now(timezone.utc).isoformat()}"
    labels = ["Blogger", "Verification", "Auto Poster"]
    html = (
        "<p>This temporary draft verifies Blogger API write and delete access. "
        "It should be deleted by the verification command.</p>"
    )
    try:
        created_post = insert_draft_post(config, title=title, html=html, labels=labels)
        post_id = created_post.get("id")
        status = created_post.get("status")
        if not post_id:
            raise RuntimeError("Blogger API response did not contain a post id.")
        if status and str(status).upper() != "DRAFT":
            raise RuntimeError(f"Verification post was not created as draft: status={status}")
        delete_post(config, post_id)
        return {
            "ok": True,
            "created": True,
            "deleted": True,
            "manual_cleanup_required": False,
            "post_id": post_id,
            "title": title,
            "status": status,
            "url": created_post.get("url"),
        }
    except Exception as exc:
        send_pushover_error_notification(
            config,
            "Blogger verification draft failed.",
            exc,
            "Check scripts/test-blogger-config.sh output and Blogger drafts for possible cleanup.",
        )
        return {
            "ok": False,
            "created": bool(created_post and created_post.get("id")),
            "deleted": False,
            "manual_cleanup_required": bool(created_post and created_post.get("id")),
            "post_id": created_post.get("id") if created_post else None,
            "title": title,
            "status": created_post.get("status") if created_post else None,
            "url": created_post.get("url") if created_post else None,
            "error": str(exc),
        }
