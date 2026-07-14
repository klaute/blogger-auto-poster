from __future__ import annotations

import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.blogger_api import find_remote_post_by_marker, insert_post, list_existing_labels, update_post
from src.label_policy import labels_for_blogger_write
from src.markdown_posts import (
    add_tracking_marker,
    combine_labels,
    content_hash_for_post,
    iter_markdown_files,
    markdown_to_html,
    PostDocument,
    read_post,
    source_id_for_post,
    tracking_marker,
)
from src.notifications import send_pushover_error_notification
from src.scheduling import (
    blogger_datetime,
    next_scheduled_datetime,
    posting_due,
    schedule_config,
    seconds_until_posting_due,
)
from src.state import load_state, local_post_record, record_posted, save_state

LOGGER = logging.getLogger("blogger-auto-poster")


def next_queue_post(config: dict[str, Any]) -> PostDocument | None:
    for path in iter_markdown_files(config):
        try:
            return read_post(path)
        except Exception as exc:
            failed_path = move_failed_path(path, config, str(exc))
            LOGGER.exception("Moved unreadable post %s to %s", path, failed_path)
            send_pushover_error_notification(
                config,
                f"Unreadable Markdown post moved to failed: {path.name}",
                exc,
                f"Fix {failed_path} and its .error.txt file, then move it back to the queue.",
            )
            continue
    return None

def move_failed_path(path: Path, config: dict[str, Any], reason: str) -> Path:
    failed_dir = Path(config.get("posting", {}).get("failed_dir", "/data/failed"))
    failed_dir.mkdir(parents=True, exist_ok=True)
    target = failed_dir / path.name
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = failed_dir / f"{path.stem}-{stamp}{path.suffix}"
    shutil.move(str(path), str(target))
    target.with_suffix(target.suffix + ".error.txt").write_text(reason + "\n", encoding="utf-8")
    return target


def move_done(post: PostDocument, config: dict[str, Any]) -> Path:
    done_dir = Path(config.get("posting", {}).get("done_dir", "/data/done"))
    done_dir.mkdir(parents=True, exist_ok=True)
    target = done_dir / post.path.name
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = done_dir / f"{post.path.stem}-{stamp}{post.path.suffix}"
    shutil.move(str(post.path), str(target))
    return target


def process_once(config: dict[str, Any]) -> bool:
    posting_config = config.get("posting", {})
    tracking_config = config.get("tracking") or {}
    state_file = Path(posting_config.get("state_file", "/data/state.json"))
    interval_seconds = int(posting_config.get("interval_seconds", 604800))
    dry_run = bool(posting_config.get("dry_run", True))
    dry_run_move_done = bool(posting_config.get("dry_run_move_done", False))
    publish_mode = str(posting_config.get("publish_mode", "draft")).lower()
    update_existing_on_change = bool(tracking_config.get("update_existing_on_change", True))

    LOGGER.info(
        "Checking Blogger queue: state_file=%s interval_seconds=%s dry_run=%s",
        state_file,
        interval_seconds,
        dry_run,
    )
    state = load_state(state_file)
    if not posting_due(config, state, interval_seconds):
        remaining = seconds_until_posting_due(config, state, interval_seconds)
        LOGGER.info(
            "No post due yet: last_post_at=%s seconds_until_due=%s",
            state.get("last_post_at"),
            remaining,
        )
        return False

    post = next_queue_post(config)
    if post is None:
        LOGGER.info("No posts found in active queue.")
        return False

    labels = combine_labels(post, config)
    if not dry_run:
        labels = labels_for_blogger_write(config, labels, list_existing_labels)
    html = markdown_to_html(post, config)
    source_id = source_id_for_post(post)
    marker = tracking_marker(config, source_id)
    tracked_html = add_tracking_marker(html, marker)
    content_hash = content_hash_for_post(post, html, labels)
    schedule_slot_index = int(schedule_config(config).get("_slot_index", 0))
    scheduled_datetime = (
        next_scheduled_datetime(config, slot_index=schedule_slot_index)
        if publish_mode == "scheduled"
        else None
    )

    local_record = local_post_record(state, source_id)
    if local_record:
        local_hash = local_record.get("content_hash")
        blogger_id = str(local_record.get("blogger_id") or "")
        if (
            update_existing_on_change
            and blogger_id
            and not dry_run
            and local_hash != content_hash
        ):
            LOGGER.info(
                "Updating existing Blogger post %s for %s because content changed.",
                blogger_id,
                post.path,
            )
            result = update_post(config, blogger_id, post, tracked_html, labels, scheduled_datetime)
            moved_to = move_done(post, config)
            result["labels"] = labels
            record_posted(
                state,
                source_id,
                post,
                moved_to,
                result,
                detected_existing=True,
                content_hash=content_hash,
                updated_existing=True,
                scheduled_datetime=scheduled_datetime,
            )
            save_state(state_file, state)
            LOGGER.info("Updated %s on Blogger and moved it to %s", post.path, moved_to)
            return True
        LOGGER.info(
            "Skipping %s because source_id %s is already tracked as Blogger post %s.",
            post.path,
            source_id,
            local_record.get("blogger_id"),
        )
        if not dry_run:
            moved_to = move_done(post, config)
            record_posted(
                state,
                source_id,
                post,
                moved_to,
                local_record,
                detected_existing=True,
                content_hash=content_hash,
                scheduled_datetime=scheduled_datetime,
            )
            save_state(state_file, state)
        return False

    if dry_run:
        LOGGER.info("DRY RUN: would post %s with labels %s", post.path, labels)
        LOGGER.info("DRY RUN: tracking source_id would be %s", source_id)
        if scheduled_datetime:
            LOGGER.info("DRY RUN: scheduled publish time would be %s", blogger_datetime(scheduled_datetime))
        if dry_run_move_done:
            moved_to = move_done(post, config)
            LOGGER.info("DRY RUN: moved %s to %s", post.path, moved_to)
        return False

    remote_post = find_remote_post_by_marker(config, marker)
    if remote_post:
        remote_post_id = str(remote_post.get("id") or "")
        if update_existing_on_change and remote_post_id:
            LOGGER.info(
                "Updating existing remote Blogger post %s for %s.",
                remote_post_id,
                post.path,
            )
            result = update_post(config, remote_post_id, post, tracked_html, labels, scheduled_datetime)
            moved_to = move_done(post, config)
            result["labels"] = labels
            record_posted(
                state,
                source_id,
                post,
                moved_to,
                result,
                detected_existing=True,
                content_hash=content_hash,
                updated_existing=True,
                scheduled_datetime=scheduled_datetime,
            )
            save_state(state_file, state)
            LOGGER.info("Updated remote Blogger post %s and moved %s to %s", remote_post_id, post.path, moved_to)
            return True
        LOGGER.info(
            "Skipping %s because source_id %s already exists remotely as Blogger post %s.",
            post.path,
            source_id,
            remote_post.get("id"),
        )
        moved_to = move_done(post, config)
        record_posted(
            state,
            source_id,
            post,
            moved_to,
            remote_post,
            detected_existing=True,
            content_hash=content_hash,
            scheduled_datetime=scheduled_datetime,
        )
        save_state(state_file, state)
        return False

    result = insert_post(config, post, tracked_html, labels, scheduled_datetime)
    moved_to = move_done(post, config)
    result["labels"] = labels
    record_posted(
        state,
        source_id,
        post,
        moved_to,
        result,
        detected_existing=False,
        content_hash=content_hash,
        scheduled_datetime=scheduled_datetime,
    )
    save_state(state_file, state)
    LOGGER.info("Posted %s to Blogger and moved it to %s", post.path, moved_to)
    return True


def run_loop(config: dict[str, Any], once: bool) -> int:
    posting_config = config.get("posting") or {}
    interval_seconds = int(posting_config.get("interval_seconds", 604800))
    check_interval_seconds = int(posting_config.get("check_interval_seconds", 3600))
    input_dir = posting_config.get("input_dir", "/data/queue")
    publish_mode = str(posting_config.get("publish_mode", "draft")).lower()
    dry_run = bool(posting_config.get("dry_run", True))
    LOGGER.info(
        "Blogger auto poster started: once=%s input_dir=%s interval_seconds=%s check_interval_seconds=%s publish_mode=%s dry_run=%s",
        once,
        input_dir,
        interval_seconds,
        check_interval_seconds,
        publish_mode,
        dry_run,
    )
    while True:
        try:
            process_once(config)
        except Exception as exc:
            LOGGER.exception("Posting cycle failed.")
            send_pushover_error_notification(
                config,
                "Blogger posting cycle failed.",
                exc,
                "Check container logs, posts/state.json and the current queue file. The post was not marked done.",
            )
        if once:
            return 0
        sleep_seconds = min(max(check_interval_seconds, 60), max(interval_seconds, 60))
        LOGGER.info("Sleeping %s seconds before next queue check.", sleep_seconds)
        time.sleep(sleep_seconds)
