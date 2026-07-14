#!/bin/sh
set -u

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-blogger-auto-poster}"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_DIR/config/config.yml}"
RESULT_FILE="$PROJECT_DIR/posts/last-blogger-test-result.json"
PUSHOVER_RESULT_FILE="$PROJECT_DIR/posts/last-pushover-test-result.json"
SUMMARY_FILE="$(mktemp "${TMPDIR:-/tmp}/blogger-auto-poster-test.XXXXXX")"

RUN_SOFTWARE=0
RUN_DRY_RUN=0
RUN_OAUTH=0
RUN_PUSHOVER=0
RUN_BLOGGER_DRAFT=0
CONTAINER_READY=0
OAUTH_CHECK_DONE=0
STEP_NO=0

cd "$PROJECT_DIR"
trap 'rm -f "$SUMMARY_FILE"' EXIT INT TERM

say() {
  printf '%s\n' "$*"
}

hr() {
  say "────────────────────────────────────────────────────────────"
}

record_result() {
  printf '%-18s %-7s %s\n' "$1" "$2" "$3" >> "$SUMMARY_FILE"
}

print_summary() {
  say ""
  hr
  say "Summary"
  hr
  if [ -s "$SUMMARY_FILE" ]; then
    cat "$SUMMARY_FILE"
  else
    say "No checks were selected."
  fi
}

fail() {
  record_result "$1" "FAIL" "$2"
  print_summary
  say ""
  say "RESULT: FAILED"
  say "Reason: $2"
  exit 1
}

pass() {
  record_result "$1" "PASS" "$2"
  say "PASS: $2"
  say ""
}

skip() {
  record_result "$1" "SKIP" "$2"
  say "SKIP: $2"
  say ""
}

section() {
  STEP_NO=$((STEP_NO + 1))
  say ""
  hr
  say "Check $STEP_NO: $1"
  hr
}

usage() {
  say "Usage: scripts/test-blogger-config.sh [--all] [--software] [--dry-run] [--oauth] [--pushover] [--blogger-draft]"
  say ""
  say "Without parameters the script runs all checks."
  say "It expects the Docker container to be running already; it does not build or start it."
  say ""
  say "Checks:"
  say "  --all             run all checks"
  say "  --software        check module imports, CLI entrypoints and management update logic"
  say "  --dry-run         check config parsing, queue access and Markdown processing"
  say "  --oauth           check local OAuth config and token refresh readiness"
  say "  --pushover        send one Pushover test message when enabled"
  say "  --blogger-draft   create one temporary Blogger draft and delete it again"
}

select_all() {
  RUN_SOFTWARE=1
  RUN_DRY_RUN=1
  RUN_OAUTH=1
  RUN_PUSHOVER=1
  RUN_BLOGGER_DRAFT=1
}

if [ "$#" -eq 0 ]; then
  select_all
fi

while [ "$#" -gt 0 ]; do
  case "$1" in
    --all)
      select_all
      ;;
    --software)
      RUN_SOFTWARE=1
      ;;
    --dry-run)
      RUN_DRY_RUN=1
      ;;
    --oauth)
      RUN_OAUTH=1
      ;;
    --pushover)
      RUN_PUSHOVER=1
      ;;
    --blogger-draft)
      RUN_BLOGGER_DRAFT=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "arguments" "Unknown parameter: $1"
      ;;
  esac
  shift
done

say "Blogger Auto Poster post-start test"
say "Project:  $PROJECT_DIR"
say "Service:  $SERVICE_NAME"
say "Config:   $CONFIG_FILE"
say "Reports:  posts/last-pushover-test-result.json, posts/last-blogger-test-result.json"
say ""
say "This test does not build or start Docker. Start the service first with scripts/build-and-verify.sh."

require_config() {
  if [ ! -f "$CONFIG_FILE" ]; then
    fail "config" "Config file is missing. Create it with: cp config/config.example.yml config/config.yml"
  fi
}

require_blogger_credentials() {
  require_config
  if grep -q 'BLOGGER_BLOG_ID\|GOOGLE_OAUTH_CLIENT_ID\|GOOGLE_OAUTH_CLIENT_SECRET\|GOOGLE_OAUTH_REFRESH_TOKEN' "$CONFIG_FILE"; then
    fail "credentials" "Config still contains placeholder Blogger values."
  fi
}

require_container() {
  if [ "$CONTAINER_READY" -eq 1 ]; then
    return
  fi

  section "Preflight"
  say "Checking docker-compose command..."
  if ! command -v docker-compose >/dev/null 2>&1; then
    fail "preflight" "docker-compose was not found in PATH."
  fi
  say "docker-compose: found"

  say "Checking running service container..."
  ps_output="$(docker-compose ps -q "$SERVICE_NAME" 2>&1)"
  ps_status=$?
  if [ "$ps_status" -ne 0 ]; then
    fail "preflight" "docker-compose ps failed: $ps_output"
  fi
  container_id="$ps_output"
  if [ -z "$container_id" ]; then
    fail "preflight" "Service $SERVICE_NAME has no container. Start it first with scripts/build-and-verify.sh or docker-compose up -d."
  fi

  inspect_output="$(docker inspect -f '{{.State.Running}}' "$container_id" 2>&1)"
  inspect_status=$?
  if [ "$inspect_status" -ne 0 ]; then
    fail "preflight" "docker inspect failed for $container_id: $inspect_output"
  fi
  running_state="$inspect_output"
  if [ "$running_state" != "true" ]; then
    say ""
    say "Last container logs:"
    docker-compose logs --tail=80 "$SERVICE_NAME"
    fail "preflight" "Container exists but is not running."
  fi
  CONTAINER_READY=1
  pass "preflight" "Container is running: $container_id"
}

print_json_summary() {
  file="$1"
  kind="$2"
  if command -v python3 >/dev/null 2>&1 && [ -s "$file" ]; then
    python3 - "$file" "$kind" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
kind = sys.argv[2]
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"Could not parse report JSON: {exc}")
    raise SystemExit(0)

if kind == "pushover":
    print(f"enabled:    {data.get('enabled')}")
    print(f"skipped:    {data.get('skipped')}")
    print(f"endpoint:   {data.get('endpoint')}")
    print(f"mode:       {data.get('mode')}")
    if data.get("error"):
        print(f"error:      {data.get('error')}")
elif kind == "blogger":
    print(f"created:    {data.get('created')}")
    print(f"deleted:    {data.get('deleted')}")
    print(f"post_id:    {data.get('post_id')}")
    print(f"status:     {data.get('status')}")
    print(f"cleanup:    {data.get('manual_cleanup_required')}")
    if data.get("error"):
        print(f"error:      {data.get('error')}")
else:
    print(json.dumps(data, indent=2, sort_keys=True))
PY
  elif [ -s "$file" ]; then
    cat "$file"
  else
    say "No report file was written."
  fi
}

run_software_check() {
  require_config
  require_container

  section "Software self-test"
  say "Checking Python syntax inside the running container..."
  if ! docker-compose exec -T "$SERVICE_NAME" sh -c 'python -m py_compile src/*.py scripts/manage-posts.py'; then
    fail "software" "Python syntax check failed in the container."
  fi

  say "Checking module boundaries, compatibility exports and management update behavior..."
  if ! docker-compose exec -T "$SERVICE_NAME" python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import importlib.util
from unittest.mock import patch
import src.blogger_auto_poster as entrypoint
import src.blogger_api as blogger_api
import src.post_management as management

spec = importlib.util.spec_from_file_location("manage_posts_cli", "scripts/manage-posts.py")
cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cli)

for name in [
    "load_config",
    "read_post",
    "process_once",
    "list_existing_labels",
    "verify_pushover_report",
    "verify_blogger_draft_cycle_report",
]:
    assert hasattr(entrypoint, name), name

with TemporaryDirectory() as tmp:
    root = Path(tmp)
    config = {
        "posting": {
            "input_dir": "/data/queue",
            "done_dir": "/data/done",
            "failed_dir": "/data/failed",
            "state_file": "/data/state.json",
            "order_file": "/data/order.txt",
        },
        "tracking": {"marker_prefix": "test-source"},
    }
    config = cli.local_management_config(config, root)
    assert config["posting"]["input_dir"] == str(root / "posts" / "queue")
    assert config["posting"]["done_dir"] == str(root / "posts" / "done")
    assert config["posting"]["state_file"] == str(root / "posts" / "state.json")

    queue = Path(config["posting"]["input_dir"])
    done = Path(config["posting"]["done_dir"])
    queue.mkdir(parents=True)
    done.mkdir(parents=True)
    post_path = queue / "demo.md"
    post_path.write_text(
        "---\ntitle: \"Demo\"\nlabels:\n  - Test\n---\n# Demo\n\nText\n",
        encoding="utf-8",
    )
    state_file = Path(config["posting"]["state_file"])
    state_file.parent.mkdir(parents=True, exist_ok=True)
    config = {
        "posting": {
            "input_dir": str(queue),
            "done_dir": str(done),
            "state_file": str(state_file),
        },
        "tracking": {"marker_prefix": "test-source"},
    }
    managed = management.collect_posts(config)[0]
    source_id = management.source_id_for_managed(managed)
    state_file.write_text(
        json.dumps({"posted_posts": {source_id: {"blogger_id": "post-123", "content_hash": "old"}}}),
        encoding="utf-8",
    )

    calls = []
    old_update_post = management.update_post
    old_list_existing_labels = management.list_existing_labels
    try:
        management.list_existing_labels = lambda config: ["Test"]
        def fake_update_post(config, post_id, post, html, labels, scheduled_datetime=None):
            calls.append((post_id, post.path.name, labels, "test-source:" in html))
            return {
                "id": post_id,
                "status": "DRAFT",
                "url": "https://example.invalid/demo",
                "title": post.title,
            }
        management.update_post = fake_update_post
        result = management.update_existing(config, managed)
    finally:
        management.update_post = old_update_post
        management.list_existing_labels = old_list_existing_labels

    assert result["id"] == "post-123"
    assert calls == [("post-123", "demo.md", ["Test"], True)]
    assert post_path.exists()
    state = json.loads(state_file.read_text(encoding="utf-8"))
    assert state["posted_posts"][source_id]["blogger_id"] == "post-123"
    assert state["posted_posts"][source_id]["status"] == "DRAFT"

    old_refresh_access_token = blogger_api.refresh_access_token
    old_list_blogger_posts = blogger_api.list_blogger_posts
    try:
        calls = []
        def fake_refresh_access_token(blogger_config):
            return "access-token"
        def fake_list_blogger_posts(config, access_token, status, page_token=None):
            calls.append((access_token, status, page_token))
            return {
                "items": [
                    {"labels": ["DIY", "Smart Home"]},
                    {"labels": ["DIY", "Blogger"]},
                ],
            }
        blogger_api.refresh_access_token = fake_refresh_access_token
        blogger_api.list_blogger_posts = fake_list_blogger_posts
        label_config = {
            "blogger": {},
            "tracking": {
                "remote_statuses": ["draft"],
                "remote_max_pages_per_status": 1,
            },
        }
        assert blogger_api.list_existing_labels(label_config) == ["Blogger", "DIY", "Smart Home"]
        assert calls == [("access-token", "draft", None)]
    finally:
        blogger_api.refresh_access_token = old_refresh_access_token
        blogger_api.list_blogger_posts = old_list_blogger_posts

print("software_self_test_ok")
PY
  then
    fail "software" "Module or management behavior self-test failed."
  fi

  say "Checking management CLI is available..."
  if ! docker-compose exec -T "$SERVICE_NAME" python scripts/manage-posts.py --help >/dev/null; then
    fail "software" "Management CLI help failed in the container."
  fi

  pass "software" "Modules, CLI and management update logic are usable."
}

run_dry_run_check() {
  require_config
  require_container

  section "Queue dry-run"
  say "Running one safe posting cycle with the configured container command path..."
  if ! docker-compose exec -T "$SERVICE_NAME" \
    python -m src.blogger_auto_poster --config /config/config.yml --once --log-level INFO; then
    fail "dry-run" "Dry-run failed. This checks config parsing, queue access and Markdown processing."
  fi
  pass "dry-run" "Dry-run completed. No Blogger post was created by this check."
}

run_oauth_check() {
  require_blogger_credentials
  require_container

  section "OAuth config"
  say "Running local OAuth configuration diagnosis inside the container..."
  if docker-compose exec -T "$SERVICE_NAME" test -f /app/scripts/diagnose-oauth-config.py; then
    if ! docker-compose exec -T "$SERVICE_NAME" \
      python /app/scripts/diagnose-oauth-config.py \
        --config /config/config.yml \
        --credentials-file /app/credentials.json \
        --skip-network; then
      fail "oauth" "Local OAuth config diagnosis failed. Fix config/config.yml or regenerate it with scripts/get_blogger_token.py."
    fi
  else
    fail "oauth" "Diagnosis script is not available in the running image. Rebuild with scripts/build-and-verify.sh."
  fi
  OAUTH_CHECK_DONE=1
  pass "oauth" "Local OAuth config looks usable."
}

run_pushover_check() {
  require_config
  require_container

  section "Pushover"
  say "Testing notification path. If Pushover is disabled, this check is reported as skipped."
  if docker-compose exec -T "$SERVICE_NAME" \
    python -m src.blogger_auto_poster \
      --config /config/config.yml \
      --verify-pushover-json \
      --log-level WARNING > "$PUSHOVER_RESULT_FILE"; then
    print_json_summary "$PUSHOVER_RESULT_FILE" "pushover"
    if grep -q '"skipped": true' "$PUSHOVER_RESULT_FILE"; then
      skip "pushover" "Pushover is disabled in config."
    else
      pass "pushover" "Pushover test notification was sent."
    fi
  else
    say "Pushover report:"
    print_json_summary "$PUSHOVER_RESULT_FILE" "pushover"
    fail "pushover" "Pushover verification failed. Full report: $PUSHOVER_RESULT_FILE"
  fi
}

run_blogger_draft_check() {
  require_blogger_credentials
  require_container

  if [ "$OAUTH_CHECK_DONE" -eq 0 ]; then
    run_oauth_check
  fi

  section "Blogger temporary draft"
  say "Creating one temporary Blogger draft, verifying the returned post id, then deleting that same draft."
  say "This does not read or upload a Markdown article from posts/queue."

  if docker-compose exec -T "$SERVICE_NAME" \
    python -m src.blogger_auto_poster \
      --config /config/config.yml \
      --verify-blogger-draft-cycle-json \
      --log-level WARNING > "$RESULT_FILE"; then
    print_json_summary "$RESULT_FILE" "blogger"
  else
    say "Blogger report:"
    print_json_summary "$RESULT_FILE" "blogger"
    if grep -q '"manual_cleanup_required": true' "$RESULT_FILE" 2>/dev/null; then
      say ""
      say "MANUAL ACTION REQUIRED: a test draft may still exist in Blogger."
      say "Open Blogger drafts and delete the verification draft shown in $RESULT_FILE."
    fi
    if grep -q 'OAuth token refresh failed' "$RESULT_FILE" 2>/dev/null; then
      say ""
      say "Likely OAuth problem:"
      say "- invalid_grant: refresh_token is wrong, revoked, expired, or from another client"
      say "- invalid_client: client_id/client_secret are wrong or do not match"
      say "- missing scope: the refresh token was not granted Blogger API access"
    fi
    fail "blogger-draft" "Blogger temporary draft verification failed. Full report: $RESULT_FILE"
  fi

  if grep -q '"ok": true' "$RESULT_FILE" && grep -q '"deleted": true' "$RESULT_FILE"; then
    pass "blogger-draft" "Temporary draft was created and deleted. Manual cleanup required: no."
    return
  fi

  fail "blogger-draft" "Draft result was not clean. Check $RESULT_FILE."
}

if [ "$RUN_SOFTWARE" -eq 1 ]; then
  run_software_check
fi

if [ "$RUN_DRY_RUN" -eq 1 ]; then
  run_dry_run_check
fi

if [ "$RUN_OAUTH" -eq 1 ]; then
  run_oauth_check
fi

if [ "$RUN_PUSHOVER" -eq 1 ]; then
  run_pushover_check
fi

if [ "$RUN_BLOGGER_DRAFT" -eq 1 ]; then
  run_blogger_draft_check
fi

print_summary
say ""
say "RESULT: OK"
exit 0
