from __future__ import annotations

import copy
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.blogger_api import (
    delete_post,
    find_remote_post_by_marker,
    get_post,
    list_existing_labels,
    publish_post,
    revert_post,
    update_post,
)
from src.label_policy import labels_for_blogger_write
from src.markdown_posts import (
    add_tracking_marker,
    combine_labels,
    content_hash_for_post,
    markdown_to_html,
    read_post,
    source_id_for_post,
    tracking_marker,
)
from src.posting_runtime import process_once
from src.state import load_state, record_posted, save_state


@dataclass
class ManagedPost:
    path: Path
    location: str
    title: str
    labels: list[str]


def posting_paths(config: dict[str, Any]) -> tuple[Path, Path, Path]:
    posting = config.get("posting") or {}
    return (
        Path(posting.get("input_dir", "posts/queue")),
        Path(posting.get("done_dir", "posts/done")),
        Path(posting.get("state_file", "posts/state.json")),
    )


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return path.with_name(f"{path.stem}-{stamp}{path.suffix}")


def collect_posts(config: dict[str, Any], locations: set[str] | None = None) -> list[ManagedPost]:
    queue_dir, done_dir, _ = posting_paths(config)
    selected_locations = locations or {"queue", "done"}
    posts: list[ManagedPost] = []
    for location, root in (("queue", queue_dir), ("backlog", queue_dir / "backlog"), ("done", done_dir)):
        if location not in selected_locations:
            continue
        if not root.exists():
            continue
        for path in sorted(root.glob("*.md")):
            post = read_post(path)
            posts.append(
                ManagedPost(
                    path=path,
                    location=location,
                    title=post.title,
                    labels=post.labels,
                )
            )
    return posts


def ensure_queue_path(config: dict[str, Any], managed: ManagedPost) -> Path:
    queue_dir, _, _ = posting_paths(config)
    queue_dir.mkdir(parents=True, exist_ok=True)
    if managed.location == "queue":
        return managed.path
    target = queue_dir / managed.path.name
    if target.exists():
        raise RuntimeError(f"Queue target already exists: {target}")
    shutil.move(str(managed.path), str(target))
    return target


def activate_backlog_post(config: dict[str, Any], managed: ManagedPost) -> dict[str, Any]:
    if managed.location != "backlog":
        raise RuntimeError(f"Only backlog posts can be activated: {managed.path}")

    queue_dir, done_dir, state_file = posting_paths(config)
    queue_dir.mkdir(parents=True, exist_ok=True)
    target = queue_dir / managed.path.name
    if target.exists():
        raise RuntimeError(f"Queue target already exists: {target}")

    source_id = source_id_for_post(read_post(managed.path))
    state = load_state(state_file)
    posted = state.setdefault("posted_posts", {})
    previous_record = posted.pop(source_id, None) if isinstance(posted, dict) else None
    if not isinstance(posted, dict):
        state["posted_posts"] = {}

    archived_done_path: str | None = None
    done_duplicate = done_dir / managed.path.name
    if done_duplicate.exists():
        archive_dir = done_dir / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_target = unique_path(archive_dir / done_duplicate.name)
        shutil.move(str(done_duplicate), str(archive_target))
        archived_done_path = str(archive_target)

    shutil.move(str(managed.path), str(target))
    activations = state.setdefault("reactivated_posts", {})
    activations[source_id] = {
        "source_name": managed.path.name,
        "queue_path": str(target),
        "archived_done_path": archived_done_path,
        "cleared_blogger_id": previous_record.get("blogger_id") if isinstance(previous_record, dict) else None,
        "reactivated_at": datetime.now(timezone.utc).isoformat(),
    }
    save_state(state_file, state)
    return {
        "source_id": source_id,
        "queue_path": str(target),
        "archived_done_path": archived_done_path,
        "cleared_local_record": bool(previous_record),
    }


def config_for_single_post(
    config: dict[str, Any],
    post_path: Path,
    publish_mode: str,
    slot_index: int = 0,
) -> tuple[dict[str, Any], Path]:
    result = copy.deepcopy(config)
    posting = result.setdefault("posting", {})
    posting["dry_run"] = False
    posting["due_mode"] = "interval"
    posting["interval_seconds"] = 0
    posting["publish_mode"] = publish_mode
    schedule = posting.setdefault("schedule", {})
    schedule["_slot_index"] = slot_index

    temp = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
    with temp:
        temp.write(post_path.name + "\n")
    order_file = Path(temp.name)
    posting["order_file"] = str(order_file)
    return result, order_file


def run_single_post(
    config: dict[str, Any],
    post_path: Path,
    publish_mode: str,
    slot_index: int = 0,
) -> bool:
    run_config, order_file = config_for_single_post(config, post_path, publish_mode, slot_index)
    try:
        return process_once(run_config)
    finally:
        order_file.unlink(missing_ok=True)


def upload_now(config: dict[str, Any], managed: ManagedPost) -> bool:
    try:
        remote_post_id(config, managed)
    except RuntimeError:
        pass
    else:
        update_existing(config, managed)
        return True

    post_path = ensure_queue_path(config, managed)
    publish_mode = str((config.get("posting") or {}).get("publish_mode", "draft")).lower()
    return run_single_post(config, post_path, publish_mode=publish_mode)


def source_id_for_managed(managed: ManagedPost) -> str:
    return source_id_for_post(read_post(managed.path))


def remote_post_id_for_path(config: dict[str, Any], path: Path) -> tuple[str, str, dict[str, Any] | None]:
    _, _, state_file = posting_paths(config)
    source_id = source_id_for_post(read_post(path))
    state = load_state(state_file)
    record = (state.get("posted_posts") or {}).get(source_id) or {}
    post_id = str(record.get("blogger_id") or "")
    if post_id:
        return source_id, post_id, record

    marker = tracking_marker(config, source_id)
    remote = find_remote_post_by_marker(config, marker)
    post_id = str(remote.get("id") or "") if remote else ""
    if post_id:
        return source_id, post_id, remote
    raise RuntimeError(f"No Blogger post id found for {path.name}.")


def remote_post_id(config: dict[str, Any], managed: ManagedPost) -> tuple[str, str, dict[str, Any] | None]:
    return remote_post_id_for_path(config, managed.path)


def has_local_blogger_link(config: dict[str, Any], managed: ManagedPost) -> bool:
    _, _, state_file = posting_paths(config)
    source_id = source_id_for_post(read_post(managed.path))
    state = load_state(state_file)
    record = (state.get("posted_posts") or {}).get(source_id) or {}
    return bool(str(record.get("blogger_id") or ""))


def delete_remote_post(config: dict[str, Any], managed: ManagedPost) -> str:
    _, _, state_file = posting_paths(config)
    source_id, post_id, _ = remote_post_id(config, managed)
    delete_post(config, post_id)
    state = load_state(state_file)
    removed = state.setdefault("removed_posts", {})
    removed[source_id] = {"blogger_id": post_id, "source_name": managed.path.name}
    posted = state.setdefault("posted_posts", {})
    posted.pop(source_id, None)
    save_state(state_file, state)
    return post_id


def update_local_record(config: dict[str, Any], source_id: str, blogger_post: dict[str, Any]) -> None:
    _, _, state_file = posting_paths(config)
    state = load_state(state_file)
    record = (state.get("posted_posts") or {}).get(source_id)
    if not isinstance(record, dict):
        return
    record["status"] = blogger_post.get("status")
    record["url"] = blogger_post.get("url")
    record["title"] = blogger_post.get("title") or record.get("title")
    save_state(state_file, state)


def publish_remote_post(config: dict[str, Any], managed: ManagedPost) -> dict[str, Any]:
    source_id, post_id, _ = remote_post_id(config, managed)
    result = publish_post(config, post_id)
    update_local_record(config, source_id, result)
    return result


def revert_remote_post(config: dict[str, Any], managed: ManagedPost) -> dict[str, Any]:
    source_id, post_id, _ = remote_post_id(config, managed)
    result = revert_post(config, post_id)
    update_local_record(config, source_id, result)
    return result


def remote_status(config: dict[str, Any], managed: ManagedPost) -> dict[str, Any]:
    source_id, post_id, record = remote_post_id(config, managed)
    remote = get_post(config, post_id)
    return {
        "source_id": source_id,
        "post_id": post_id,
        "local_record": record,
        "remote": remote,
    }


def update_existing(config: dict[str, Any], managed: ManagedPost) -> dict[str, Any]:
    post_path = managed.path
    _, _, state_file = posting_paths(config)
    source_id, post_id, _ = remote_post_id_for_path(config, post_path)
    post = read_post(post_path)
    labels = labels_for_blogger_write(config, combine_labels(post, config), list_existing_labels)
    html = markdown_to_html(post, config)
    tracked_html = add_tracking_marker(html, tracking_marker(config, source_id))
    content_hash = content_hash_for_post(post, html, labels)
    result = update_post(config, post_id, post, tracked_html, labels)
    result["labels"] = labels

    state = load_state(state_file)
    record_posted(
        state,
        source_id,
        post,
        post_path,
        result,
        detected_existing=True,
        content_hash=content_hash,
        updated_existing=True,
    )
    save_state(state_file, state)
    return result
