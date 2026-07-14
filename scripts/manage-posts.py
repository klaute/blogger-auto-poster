#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.blogger_api import list_existing_labels
from src.config import load_config
from src.post_management import (
    ManagedPost,
    activate_backlog_post,
    collect_posts,
    delete_remote_post,
    has_local_blogger_link,
    publish_remote_post,
    remote_status,
    revert_remote_post,
    update_existing,
    upload_now,
)


QUIT_VALUES = {"q", "quit", "exit"}


def map_container_path_to_repo(path_value: str, project_root: Path) -> str:
    container_paths = {
        "/data/queue": project_root / "posts" / "queue",
        "/data/done": project_root / "posts" / "done",
        "/data/failed": project_root / "posts" / "failed",
        "/data/state.json": project_root / "posts" / "state.json",
        "/data/order.txt": project_root / "posts" / "order.txt",
    }
    mapped = container_paths.get(path_value)
    if mapped is None:
        return path_value
    return str(mapped)


def local_management_config(config: dict[str, Any], project_root: Path) -> dict[str, Any]:
    result = copy.deepcopy(config)
    posting = result.setdefault("posting", {})
    for key in ("input_dir", "done_dir", "failed_dir", "state_file", "order_file"):
        value = posting.get(key)
        if isinstance(value, str):
            posting[key] = map_container_path_to_repo(value, project_root)
    return result


def print_path_summary(config: dict[str, Any]) -> None:
    posting = config.get("posting") or {}
    print("Paths:")
    print(f"  queue: {posting.get('input_dir', 'posts/queue')}")
    print(f"  done:  {posting.get('done_dir', 'posts/done')}")
    print(f"  state: {posting.get('state_file', 'posts/state.json')}")
    print(f"  publish_mode: {posting.get('publish_mode', 'draft')}")


def print_posts(posts: list[ManagedPost]) -> None:
    print("Posts:")
    if not posts:
        print("  No Markdown posts found.")
        return
    for index, post in enumerate(posts, start=1):
        labels = ", ".join(post.labels)
        print(f"{index:3}. [{post.location:5}] {post.path.name} | {post.title} | {labels}")


def choose_from_locations(
    config: dict[str, Any],
    locations: set[str],
    heading: str,
    *,
    show_links: bool = False,
    require_link: bool = False,
) -> ManagedPost | None:
    print_section_separator()
    print(heading)
    posts = collect_posts(config, locations=locations)
    print_posts_with_links(config, posts) if show_links else print_posts(posts)
    if not posts and "queue" in locations:
        print_backlog_hint(config)
    if not posts:
        return None
    post = choose_post(posts)
    if post is None:
        return None
    if require_link and not has_local_blogger_link(config, post):
        print_result(
            f"{post.path.name} is not linked to a Blogger post. Upload it again first or select a linked post."
        )
        return None
    return post


def print_section_separator() -> None:
    print("")
    print("-" * 80)
    print("")


def read_input(prompt: str) -> str | None:
    try:
        return input(prompt).strip()
    except EOFError:
        return None


def is_quit_value(value: str | None) -> bool:
    return value is None or value.lower() in QUIT_VALUES


def choose_post(posts: list[ManagedPost], prompt: str = "Post number or filename, or q to cancel: ") -> ManagedPost | None:
    if not posts:
        print_result("No posts available.")
        return None
    value = read_input(prompt)
    if value is None or not value or is_quit_value(value):
        print_result("Selection aborted.")
        return None
    if value.isdigit():
        index = int(value)
        if 1 <= index <= len(posts):
            return posts[index - 1]
        print_result(f"Invalid post number {index}. Choose a number from 1 to {len(posts)}.")
        return None
    matches = [post for post in posts if post.path.name == value or value.lower() in post.path.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        print_result(f"No post matches: {value}")
        return None
    print_posts(matches)
    print_result("Several posts match. Use the exact number from the full list.")
    return None


def print_posts_with_links(config: dict[str, Any], posts: list[ManagedPost]) -> None:
    print("Posts:")
    if not posts:
        print("  No Markdown posts found.")
        return
    for index, post in enumerate(posts, start=1):
        labels = ", ".join(post.labels)
        link_state = "linked" if has_local_blogger_link(config, post) else "not linked"
        print(f"{index:3}. [{post.location:5}] [{link_state:10}] {post.path.name} | {post.title} | {labels}")


def print_backlog_hint(config: dict[str, Any]) -> None:
    posting = config.get("posting") or {}
    queue_dir = Path(posting.get("input_dir", "posts/queue"))
    backlog_dir = queue_dir / "backlog"
    if not backlog_dir.exists():
        return
    backlog_count = len(sorted(backlog_dir.glob("*.md")))
    if backlog_count:
        print(f"  Backlog contains {backlog_count} Markdown posts and is intentionally hidden here.")
        print(f"  Move one file from {backlog_dir} to {queue_dir} to make it uploadable.")


def confirm(prompt: str, expected: str = "YES") -> bool:
    value = read_input(f"{prompt} Type {expected}, or q to cancel: ")
    if value is None or is_quit_value(value):
        return False
    return value == expected


def menu() -> str:
    print_section_separator()
    print("Actions:")
    print("1. Upload or update one selected post using configured publish_mode")
    print("2. Take one selected Blogger post offline by reverting it to draft")
    print("3. Publish one selected Blogger draft")
    print("4. Update one existing linked Blogger post")
    print("5. Show Blogger status and local tracking link for one selected post")
    print("6. Show existing Blogger labels")
    print("7. Activate one backlog post for upload")
    print("8. Danger: delete one linked Blogger post")
    print("q. quit")
    value = read_input("Action: ")
    if value is None:
        return "q"
    return value.lower()


def print_result(message: str) -> None:
    print("")
    print("Result:")
    print(f"  {message}")


def show_remote_status(config: dict, managed: ManagedPost) -> None:
    status = remote_status(config, managed)
    remote = status["remote"]
    local_record = status.get("local_record") or {}
    print(f"linked:    {managed.path.name} -> Blogger post {status['post_id']}")
    print(f"source_id: {status['source_id']}")
    print(f"post_id:   {status['post_id']}")
    print(f"status:    {remote.get('status')}")
    print(f"title:     {remote.get('title')}")
    print(f"url:       {remote.get('url')}")
    if local_record:
        print(f"state:     tracked locally as {local_record.get('status')}")


def run_remote_action(action: Callable[[], None]) -> None:
    try:
        action()
    except Exception as exc:
        print_result(f"{type(exc).__name__}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yml")
    parser.add_argument(
        "--use-config-paths",
        action="store_true",
        help="Use posting paths from config as-is. By default /data/... container paths are mapped to repo-local posts/...",
    )
    args = parser.parse_args()
    config = load_config(Path(args.config))
    if not args.use_config_paths:
        config = local_management_config(config, PROJECT_ROOT)

    print_path_summary(config)
    while True:
        action = menu()
        if action in {"q", "quit", "exit"}:
            return 0
        if action == "1":
            managed = choose_from_locations(config, {"queue"}, "Select an active queue post:")
            if managed is None:
                continue
            changed = upload_now(config, managed)
            if changed:
                print_result(f"Uploaded or updated Blogger post for {managed.path.name}.")
            else:
                print_result(f"No Blogger write was needed for {managed.path.name}; check logs/state.")
        elif action == "2":
            managed = choose_from_locations(
                config,
                {"done"},
                "Select a done post to take offline:",
                show_links=True,
                require_link=True,
            )
            if managed is None:
                continue
            def offline() -> None:
                if confirm(f"Take Blogger post for {managed.path.name} offline by reverting it to draft?", "DRAFT"):
                    result = revert_remote_post(config, managed)
                    print_result(f"Offline/draft: Blogger post {result.get('id')} now has status {result.get('status')}.")
                else:
                    print_result("Aborted.")
            run_remote_action(offline)
        elif action == "3":
            managed = choose_from_locations(
                config,
                {"done"},
                "Select a done post to publish:",
                show_links=True,
                require_link=True,
            )
            if managed is None:
                continue
            def publish() -> None:
                if confirm(f"Publish Blogger post for {managed.path.name}?", "PUBLISH"):
                    result = publish_remote_post(config, managed)
                    print_result(f"Published Blogger post {result.get('id')} with status {result.get('status')}.")
                else:
                    print_result("Aborted.")
            run_remote_action(publish)
        elif action == "4":
            managed = choose_from_locations(
                config,
                {"done"},
                "Select a done post to update:",
                show_links=True,
                require_link=True,
            )
            if managed is None:
                continue
            def update() -> None:
                if confirm(f"Update existing Blogger post for {managed.path.name}?", "UPDATE"):
                    result = update_existing(config, managed)
                    print_result(f"Updated Blogger post {result.get('id')}.")
                else:
                    print_result("Aborted.")
            run_remote_action(update)
        elif action == "5":
            managed = choose_from_locations(
                config,
                {"done"},
                "Select a done post:",
                show_links=True,
                require_link=True,
            )
            if managed is None:
                continue
            run_remote_action(lambda: show_remote_status(config, managed))
        elif action == "6":
            labels = list_existing_labels(config)
            if not labels:
                print_result("No Blogger labels found.")
            else:
                print("")
                print("Blogger labels:")
                for label in labels:
                    print(f"  {label}")
        elif action == "7":
            managed = choose_from_locations(config, {"backlog"}, "Select a backlog post to activate:")
            if managed is None:
                continue
            def activate() -> None:
                if confirm(
                    f"Move {managed.path.name} from backlog to queue and clear its local Blogger link?",
                    "ACTIVATE",
                ):
                    result = activate_backlog_post(config, managed)
                    details = [f"Activated {managed.path.name} for upload at {result['queue_path']}."]
                    if result.get("archived_done_path"):
                        details.append(f"Archived done duplicate at {result['archived_done_path']}.")
                    if result.get("cleared_local_record"):
                        details.append("Cleared the local Blogger tracking record for this source.")
                    print_result(" ".join(details))
                else:
                    print_result("Aborted.")
            run_remote_action(activate)
        elif action == "8":
            managed = choose_from_locations(
                config,
                {"done"},
                "Select a done post to delete:",
                show_links=True,
                require_link=True,
            )
            if managed is None:
                continue
            def delete() -> None:
                if confirm(f"Delete Blogger post for {managed.path.name}?", "DELETE"):
                    post_id = delete_remote_post(config, managed)
                    print_result(f"Deleted Blogger post {post_id}.")
                else:
                    print_result("Aborted.")
            run_remote_action(delete)
        else:
            print_result(f"Unknown action: {action}")


if __name__ == "__main__":
    sys.exit(main())
