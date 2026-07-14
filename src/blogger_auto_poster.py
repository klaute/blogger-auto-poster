from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.blogger_api import (
    delete_post,
    find_remote_post_by_marker,
    get_post,
    insert_draft_post,
    insert_post,
    list_blogger_posts,
    list_existing_labels,
    publish_post,
    refresh_access_token,
    response_error_detail,
    revert_post,
    update_post,
    verify_blogger_draft_cycle,
    verify_blogger_draft_cycle_report,
)
from src.config import load_config
from src.markdown_posts import (
    add_tracking_marker,
    combine_labels,
    content_hash_for_post,
    first_heading,
    iter_markdown_files,
    markdown_to_html,
    normalize_labels,
    parse_frontmatter,
    PostDocument,
    read_post,
    should_ignore,
    sort_by_order_file,
    source_id_for_post,
    tracking_marker,
)
from src.notifications import (
    compact_error,
    normalize_pushover_url,
    pushover_dedupe_key,
    pushover_endpoint,
    pushover_mode,
    send_pushover_error_notification,
    send_pushover_message,
    send_pushover_upload_notification,
    verify_pushover_report,
)
from src.posting_runtime import move_done, move_failed_path, next_queue_post, process_once, run_loop
from src.scheduling import (
    blogger_datetime,
    is_due,
    next_scheduled_datetime,
    next_weekly_due_datetime,
    parse_schedule_time,
    parse_schedule_weekday,
    posting_due,
    schedule_config,
    schedule_timezone,
    seconds_until_due,
    seconds_until_posting_due,
    WEEKDAYS,
)
from src.state import load_state, local_post_record, posted_posts_state, record_posted, save_state


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--verify-blogger-draft-cycle",
        action="store_true",
        help="Create one Blogger draft post, verify it, delete it, then exit.",
    )
    parser.add_argument(
        "--verify-blogger-draft-cycle-json",
        action="store_true",
        help="Create/delete a Blogger draft and print a JSON result.",
    )
    parser.add_argument(
        "--verify-pushover-json",
        action="store_true",
        help="Send one Pushover test notification when enabled and print a JSON result.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    config = load_config(Path(args.config))
    if args.verify_pushover_json:
        result = verify_pushover_report(config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    if args.verify_blogger_draft_cycle_json:
        result = verify_blogger_draft_cycle_report(config)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result.get("ok") else 1
    if args.verify_blogger_draft_cycle:
        verify_blogger_draft_cycle(config)
        return 0
    return run_loop(config, once=args.once)


if __name__ == "__main__":
    sys.exit(main())
