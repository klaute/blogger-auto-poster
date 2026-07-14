from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.markdown_posts import PostDocument
from src.scheduling import blogger_datetime


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp_path.replace(path)


def posted_posts_state(state: dict[str, Any]) -> dict[str, Any]:
    posted_posts = state.setdefault("posted_posts", {})
    if not isinstance(posted_posts, dict):
        posted_posts = {}
        state["posted_posts"] = posted_posts
    return posted_posts


def local_post_record(state: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    record = posted_posts_state(state).get(source_id)
    return record if isinstance(record, dict) else None


def record_posted(
    state: dict[str, Any],
    source_id: str,
    post: PostDocument,
    moved_to: Path,
    blogger_post: dict[str, Any],
    detected_existing: bool,
    content_hash: str,
    updated_existing: bool = False,
    scheduled_datetime: datetime | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "source": str(post.path),
        "source_name": post.path.name,
        "done_path": str(moved_to),
        "blogger_id": blogger_post.get("id") or blogger_post.get("blogger_id"),
        "url": blogger_post.get("url"),
        "title": blogger_post.get("title") or post.title,
        "status": blogger_post.get("status"),
        "labels": blogger_post.get("labels") or [],
        "content_hash": content_hash,
        "scheduled_for": blogger_datetime(scheduled_datetime),
        "recorded_at": now,
        "detected_existing": detected_existing,
        "updated_existing": updated_existing,
    }
    posted_posts_state(state)[source_id] = record
    if updated_existing:
        state["last_update_at"] = now
        state["last_update"] = record
    elif detected_existing:
        state["last_duplicate"] = record
    else:
        state["last_post_at"] = now
        state["last_post"] = record
