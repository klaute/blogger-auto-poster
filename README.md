# Blogger Auto Poster

Automated uploader for prepared Markdown posts to Blogger.

The project is designed for a simple workflow:

- keep draft articles as Markdown files
- review and activate only the files that should be uploaded
- upload one post at a configured interval
- create Blogger drafts, live posts, or scheduled posts
- track uploaded posts locally so existing Blogger posts can be updated instead of duplicated

## Repository Layout

```text
.
├── config/
│   └── config.example.yml
├── posts/
│   ├── queue/
│   │   ├── backlog/
│   │   └── ignore/
│   ├── done/
│   ├── failed/
│   └── order.txt
├── scripts/
├── src/
├── .gitattributes
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

Important paths:

- `.gitattributes`: keeps exported text files on LF line endings.
- `.gitignore`: keeps credentials, local config, runtime state, reports, caches, and virtual environments out of Git.
- `config/config.example.yml`: versioned example configuration.
- `config/config.yml`: local runtime configuration with real values. It is ignored by Git.
- `credentials.json`: local Google OAuth client file. It is ignored by Git.
- `posts/queue/`: active Markdown files. The poster may upload these files.
- `posts/queue/backlog/`: parked drafts. The server ignores these files; the management script can select them explicitly.
- `posts/queue/ignore/`: ignored Markdown files or source material.
- `posts/done/`: locally processed Markdown files.
- `posts/failed/`: unreadable or failed Markdown files.
- `posts/failed/*.error.txt`: error detail files written next to failed Markdown files.
- `posts/order.txt`: optional upload order for active queue files.
- `posts/state.json`: local upload and tracking state. It is ignored by Git.
- `posts/last-blogger-test-result.json`: last Blogger verification report. It is ignored by Git.
- `posts/last-pushover-test-result.json`: last Pushover verification report. It is ignored by Git.
- `Dockerfile`: builds the Python runtime image.
- `docker-compose.yml`: mounts `./config` to `/config`, `./posts` to `/data`, and `./credentials.json` to `/app/credentials.json`.
- `requirements.txt`: Python package list installed by the Docker image and local venv setup.

`posts/done/` only means that a Markdown file was processed locally. A done file may still be linked to a Blogger post, but it may also be unlinked if the remote post was deleted or can no longer be found.

## Architecture

The code is split into small modules:

- `src/config.py`: loads YAML configuration.
- `src/markdown_posts.py`: reads Markdown, frontmatter, labels, HTML rendering, and tracking markers.
- `src/state.py`: reads and writes the local state file.
- `src/scheduling.py`: interval, weekly schedule, and Blogger timestamp logic.
- `src/notifications.py`: Pushover proxy integration and notifications.
- `src/blogger_api.py`: Google OAuth and Blogger API calls.
- `src/posting_runtime.py`: automatic posting loop, queue processing, and file moves.
- `src/post_management.py`: manual management actions for local posts and Blogger posts.
- `scripts/manage-posts.py`: interactive user interface only.
- `src/blogger_auto_poster.py`: container CLI entry point and compatibility exports.

The separation is intentionally simple: the interactive UI asks for input, Markdown logic does not know about Blogger, Blogger API code does not know about terminal prompts, and the runtime loop orchestrates the pieces.

## Quick Start

Create a local config file:

```sh
cp config/config.example.yml config/config.yml
```

Then edit `config/config.yml` and set at least:

- `blogger.blog_id`
- `blogger.client_id`
- `blogger.client_secret`
- `blogger.refresh_token`

Build the local Python environment:

```sh
scripts/update-venv.sh
```

Load it into the current shell:

```sh
. scripts/load-venv.sh
```

Alternatively, call tools explicitly through `.venv/bin/python`.

Start the container:

```sh
docker-compose up -d
```

Check logs:

```sh
docker-compose logs -f blogger-auto-poster
```

## Google Blogger OAuth

The tool does not log in with a Blogger username and password. It uses the official Blogger API with Google OAuth 2.0.

Required OAuth scope:

```text
https://www.googleapis.com/auth/blogger
```

Setup:

1. Create or select a Google Cloud project.
2. Enable the Blogger API for that project.
3. Create an OAuth client of type `Desktop app`.
4. Download the OAuth client file and save it as `credentials.json` in the project root.
5. Generate a refresh token once.
6. Store `client_id`, `client_secret`, and `refresh_token` in `config/config.yml`.

Generate a token on a machine where the browser can open the local callback URL:

```sh
scripts/get_blogger_token.py
```

The helper reads `credentials.json`, prints a Google login URL, waits for the callback on `http://127.0.0.1:8765/callback`, and updates:

```yaml
blogger:
  client_id: "..."
  client_secret: "..."
  refresh_token: "GOOGLE_OAUTH_REFRESH_TOKEN"
```

If the browser runs on another machine, use:

```sh
scripts/extract-refresh-key.py
```

Open the printed Google URL in the browser, copy the full callback URL after login, and paste it into the script. The browser may show a connection error for `127.0.0.1`; that is fine as long as the callback URL contains `code=...`.

Important: the `code=...` value from the callback URL is only a temporary authorization code. It often starts with `4/...`. Do not put that value into `config/config.yml`. The helper exchanges it for a real refresh token.

You can also run the OAuth module directly:

```sh
python -m src.oauth_setup --credentials-file credentials.json --update-config config/config.yml
```

Secrets must stay local:

- `config/config.yml`
- `credentials.json`
- OAuth refresh tokens
- OAuth client secrets

These files are ignored by Git.

If the container is already running and `config/config.yml` changes, restart it:

```sh
docker-compose restart blogger-auto-poster
```

## Configuration

Important fields in `config/config.yml`:

```yaml
blogger:
  blog_id: "BLOGGER_BLOG_ID"
  client_id: "GOOGLE_OAUTH_CLIENT_ID"
  client_secret: "GOOGLE_OAUTH_CLIENT_SECRET"
  refresh_token: "GOOGLE_OAUTH_REFRESH_TOKEN"

posting:
  input_dir: "/data/queue"
  done_dir: "/data/done"
  failed_dir: "/data/failed"
  state_file: "/data/state.json"
  order_file: "/data/order.txt"
  due_mode: "interval"
  interval_seconds: 604800
  check_interval_seconds: 3600
  dry_run: true
  dry_run_move_done: false
  publish_mode: "draft"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
  ignore_dirs:
    - "ignore"
    - "backlog"

tracking:
  marker_prefix: "blogger-auto-poster-source-id"
  remote_check_enabled: true
  update_existing_on_change: true
  remote_statuses:
    - "draft"
    - "live"
    - "scheduled"
  remote_max_pages_per_status: 10

notifications:
  pushover:
    enabled: false
    host: "pushover-app-server"
    port: 8090
    mode: "get"
    token: "PUSHOVER_APP_TOKEN"
    app_name: "Blogger Auto Poster"
    dedupe_prefix: "blogger-auto-poster"
    timeout_seconds: 10
```

Key meanings:

- `posting.dry_run`: when `true`, no Blogger write is made.
- `posting.publish_mode`: `draft`, `live`, or `scheduled`.
- `posting.due_mode`: `interval` or `weekly_schedule`.
- `posting.interval_seconds`: delay between successful posts. `604800` is one week.
- `posting.check_interval_seconds`: how often the long-running container wakes up.
- `posting.ignore_dirs`: subdirectories under `posting.input_dir` that are skipped.
- `tracking.remote_check_enabled`: checks Blogger for existing posts with the invisible source marker.
- `tracking.update_existing_on_change`: updates an existing Blogger post when the source exists and content changed.
- `notifications.pushover.enabled`: sends Pushover notifications through the internal Pushover proxy.

## Markdown Posts

Each post is one Markdown file with YAML frontmatter:

```markdown
---
title: "Example Post"
labels:
  - Example
  - Blogger
  - Automation
---

# Example Post

Post body...
```

Required fields:

- `title`: Blogger post title.
- `labels`: Blogger labels.

Labels are stored in each Markdown file. The runtime config does not contain label rules and does not add labels automatically.

Before real Blogger writes, the tool reads existing Blogger labels and aligns local label casing. Example: if Blogger already has `Smart Home` and the Markdown file contains `smart home`, the upload uses `Smart Home`. New labels are allowed.

## Queue Model

Local publishing permission is folder based:

- `posts/queue/`: active posts. The server may process these files.
- `posts/queue/backlog/`: parked posts. The server ignores these files until they are selected by the management script.
- `posts/queue/ignore/`: ignored posts or source material.
- `posts/done/`: locally processed posts.

To publish a parked post, use action 1 in `scripts/manage-posts.py`. The action lists active queue files, linked done files that can be updated, and parked backlog files that can be activated and uploaded in one flow.

After a successful upload, the file is moved to `posts/done/`. Unreadable files are moved to `posts/failed/`.

## Duplicate Tracking

The tool creates a stable `source_id` from the Markdown filename and writes it into the Blogger post as an invisible HTML comment:

```html
<!-- blogger-auto-poster-source-id: example-post.md:... -->
```

Before a real upload, the tool checks:

1. Is the `source_id` already present in `posts/state.json`?
2. If not, can the Blogger API find a post with the same marker in `draft`, `live`, or `scheduled` posts?
3. If an existing post is found and `tracking.update_existing_on_change: true`, update that post.
4. If no existing post is found, create a new post.

If a Blogger post was deleted externally or through the delete action, the local done file has no valid Blogger post ID anymore. The management script shows it as `not linked`. Such a file cannot be taken offline, published, updated, or deleted remotely.

To upload or update content, use action 1 in the management script. For linked files in `posts/done/`, action 1 updates the existing Blogger post. For backlog files, action 1 writes to Blogger first, then moves the file from `posts/queue/backlog/` to `posts/done/` and archives any same-named old `posts/done/` file under `posts/done/archive/`. Existing Blogger tracking is kept, so an edited backlog file updates the linked Blogger post instead of creating a duplicate. If the locally tracked Blogger post was deleted remotely and Blogger returns `404`, action 1 recreates the post and stores the new Blogger post ID.

## Management Script

Manual queue and Blogger operations are handled by:

```sh
scripts/manage-posts.py --config config/config.yml
```

Action 1 lists Markdown files from:

- `posts/queue`
- linked files in `posts/done`
- `posts/queue/backlog`

Actions 2 to 5 and 8 list Markdown files from:

- `posts/done`

It does not list:

- `posts/queue/ignore`

Done entries are marked as:

- `linked`: a Blogger post ID is known locally.
- `not linked`: the file exists locally, but no current Blogger post ID is known.

Available actions:

1. Upload or update one selected queue/backlog/done post using the configured `publish_mode`.
2. Take one selected Blogger post offline by reverting it to draft.
3. Publish one selected Blogger draft.
4. Update one existing linked Blogger post.
5. Show Blogger status and local tracking link for one selected post.
6. Show existing Blogger labels.
7. Activate one backlog post for later upload.
8. Delete one linked Blogger post.

Actions 2 to 5 and 8 require an existing Blogger link. If a selected done file is `not linked`, the script stops that action and explains that a new upload is required first.

Action 1 is the normal path for publishing, reposting, or updating content. It can update a linked done file directly, process an active queue file, or write a selected backlog file to Blogger and then move it to `posts/done/`. Action 7 is only for preparing a backlog file for a later server cycle or a later manual upload. It moves the selected file to `posts/queue/`, keeps existing local Blogger tracking for that source, and archives a same-named local `posts/done/` duplicate under `posts/done/archive/`.

When run locally, the management script maps Docker paths from the config to repository paths:

- `/data/queue` -> `posts/queue`
- `/data/done` -> `posts/done`
- `/data/state.json` -> `posts/state.json`

Use `--use-config-paths` only when you intentionally want to use the paths exactly as written in the config.

## Scheduling and Publish Modes

For safe testing:

```yaml
posting:
  dry_run: true
  publish_mode: "draft"
```

For real Blogger drafts:

```yaml
posting:
  dry_run: false
  publish_mode: "draft"
```

For immediate publishing:

```yaml
posting:
  dry_run: false
  publish_mode: "live"
```

For scheduled Blogger posts:

```yaml
posting:
  dry_run: false
  publish_mode: "scheduled"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
```

If real uploads should only start on a fixed weekday and time:

```yaml
posting:
  dry_run: false
  due_mode: "weekly_schedule"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
```

The server does not maintain a separate planning list. The order comes from `posts/order.txt`; files not listed there follow alphabetically by filename.

## Pushover Notifications

The tool can send notifications before real Blogger write attempts and on errors. It talks to an internal Pushover proxy service, not directly to the public Pushover API.

Example config:

```yaml
notifications:
  pushover:
    enabled: true
    host: "pushover-app-server"
    port: 8090
    mode: "get"
    token: "PUSHOVER_APP_TOKEN"
    app_name: "Blogger Auto Poster"
    dedupe_prefix: "blogger-auto-poster"
```

Notifications are sent for:

- real upload attempts as draft, live post, or scheduled post
- updates of existing Blogger posts
- posting loop failures
- failed Blogger verification draft tests
- unreadable Markdown files moved to `failed`

Dry-runs do not send upload-start notifications because no upload attempt is made. A failed Pushover request is logged but does not block the Blogger upload.

## Testing

Build, start, and run a safe dry-run:

```sh
scripts/build-and-verify.sh
```

This script:

- builds the Docker image
- starts the container
- checks that the container is running
- runs a safe `--once` dry-run inside the container

It does not create a Blogger post unless explicitly requested:

```sh
VERIFY_BLOGGER_DRAFT=1 scripts/build-and-verify.sh
```

Credential and runtime checks:

```sh
scripts/test-blogger-config.sh
```

Without arguments, the script runs all checks. Individual checks:

```sh
scripts/test-blogger-config.sh --software
scripts/test-blogger-config.sh --dry-run
scripts/test-blogger-config.sh --oauth
scripts/test-blogger-config.sh --pushover
scripts/test-blogger-config.sh --blogger-draft
scripts/test-blogger-config.sh --all
```

The script reports each step and prints a compact PASS/SKIP/FAIL summary.

The Blogger draft verification creates one temporary draft post with a title like `Blogger Auto Poster Verification ...`, checks that Blogger returned a post ID, and deletes that draft again. It does not upload a Markdown article from the queue.

## Useful Commands

Run one local cycle without Docker:

```sh
python -m src.blogger_auto_poster --config config/config.yml --once
```

Run the long-running process manually:

```sh
python -m src.blogger_auto_poster --config config/config.yml --log-level INFO
```

Normalize prepared Markdown files after manual edits:

```sh
python -m src.prepare_posts --config config/config.example.yml --input-dir posts/queue/backlog
```

## Script Reference

| Script | Needs | Writes | Purpose |
| --- | --- | --- | --- |
| `scripts/update-venv.sh` | `requirements.txt` | `.venv/` | Rebuilds the local Python virtual environment and installs dependencies. |
| `scripts/load-venv.sh` | `.venv/` | current shell environment | Loads the virtual environment into the current shell. Use `. scripts/load-venv.sh`. |
| `scripts/get_blogger_token.py` | `credentials.json`, `config/config.yml` | `config/config.yml` | Runs the OAuth flow and stores Blogger OAuth values in the local config. |
| `scripts/extract-refresh-key.py` | `credentials.json`, `config/config.yml` | `config/config.yml` | Exchanges a copied Google callback URL for a refresh token. |
| `scripts/diagnose-oauth-config.py` | `config/config.yml`, optional `credentials.json` | stdout only | Prints a masked OAuth diagnosis. |
| `scripts/manage-posts.py` | `config/config.yml`, `posts/queue`, `posts/queue/backlog`, `posts/done`, `posts/state.json` | `posts/state.json`, Blogger posts, local file moves, `posts/done/archive` | Interactive queue and Blogger post management. |
| `scripts/build-and-verify.sh` | `docker-compose`, `Dockerfile`, `config/config.yml`, `credentials.json` | Docker image/container, optional test draft | Builds and starts the container, then runs a safe dry-run. |
| `scripts/test-blogger-config.sh` | running `docker-compose` service, `config/config.yml`, optional `credentials.json` | `posts/last-blogger-test-result.json`, `posts/last-pushover-test-result.json` | Runs software, dry-run, OAuth, Pushover, and Blogger draft checks. |

The scripts intentionally share the same core modules under `src/`. The Docker process, test script, and management script do not implement separate Blogger or Markdown logic.

## Public GitHub Repository

The sanitized public version is available here:

```text
https://github.com/klaute/blogger-auto-poster
```
