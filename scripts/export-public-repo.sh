#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$(cd "$SOURCE_DIR/.." && pwd)/blogger-auto-poster-public"
REMOTE_URL=""
PUSH_REMOTE=0
FORCE=0
COMMIT_MESSAGE="Initial public Blogger Auto Poster export"

usage() {
  cat <<'USAGE'
Usage:
  scripts/export-public-repo.sh [--target PATH] [--remote URL] [--push] [--force]

Creates a sanitized public repository export:
- copies only the Blogger Auto Poster tool code and documentation
- does not copy real posts, state, credentials, local config, or test reports
- creates one neutral example Markdown post
- initializes a new Git repository and commits the export

Examples:
  scripts/export-public-repo.sh --target ../blogger-auto-poster-public
  scripts/export-public-repo.sh --remote git@github.com:klaute/blogger-auto-poster.git --push
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --target)
      TARGET_DIR="$2"
      shift 2
      ;;
    --remote)
      REMOTE_URL="$2"
      shift 2
      ;;
    --push)
      PUSH_REMOTE=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

TARGET_DIR="$(cd "$(dirname "$TARGET_DIR")" && pwd)/$(basename "$TARGET_DIR")"

say() {
  printf '%s\n' "$*"
}

section() {
  say ""
  say "--------------------------------------------------------------------------------"
  say "$*"
  say "--------------------------------------------------------------------------------"
}

SOURCE_ITEMS=(
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
  config/config.example.yml
  src
  scripts/build-and-verify.sh
  scripts/diagnose-oauth-config.py
  scripts/extract-refresh-key.py
  scripts/export-public-repo.sh
  scripts/get_blogger_token.py
  scripts/load-venv.sh
  scripts/manage-posts.py
  scripts/test-blogger-config.sh
  scripts/update-venv.sh
)

EXCLUDED_ITEMS=(
  config/config.yml
  credentials.json
  posts/queue/backlog
  posts/queue/ignore
  posts/done
  posts/failed
  posts/state.json
  posts/last-blogger-test-result.json
  posts/last-pushover-test-result.json
  pushover_credentials.txt
)

section "Blogger Auto Poster public export"
say "Source: $SOURCE_DIR"
say "Target: $TARGET_DIR"
if [ -n "$REMOTE_URL" ]; then
  say "Remote: $REMOTE_URL"
else
  say "Remote: not configured"
fi
if [ "$PUSH_REMOTE" -eq 1 ]; then
  say "Push: enabled"
else
  say "Push: disabled"
fi

if [ -e "$TARGET_DIR" ]; then
  if [ "$FORCE" -ne 1 ]; then
    echo "Target already exists: $TARGET_DIR" >&2
    echo "Use --force to replace it." >&2
    exit 1
  fi
  section "Step 1/6: replacing existing target"
  say "Removing existing export directory: $TARGET_DIR"
  rm -rf "$TARGET_DIR"
else
  section "Step 1/6: preparing target"
  say "Creating export directory: $TARGET_DIR"
fi

mkdir -p "$TARGET_DIR"

copy_path() {
  local rel_path="$1"
  mkdir -p "$TARGET_DIR/$(dirname "$rel_path")"
  cp -R "$SOURCE_DIR/$rel_path" "$TARGET_DIR/$rel_path"
}

section "Step 2/6: copying allowlisted tool files"
for item in "${SOURCE_ITEMS[@]}"; do
  say "Copy: $item"
  copy_path "$item"
done

say ""
say "Not copied:"
for item in "${EXCLUDED_ITEMS[@]}"; do
  say "- $item"
done

mkdir -p "$TARGET_DIR/posts/queue" "$TARGET_DIR/posts/done" "$TARGET_DIR/posts/failed"

section "Step 3/6: writing neutral example post"
say "Create: posts/queue/example-post.md"
cat > "$TARGET_DIR/posts/queue/example-post.md" <<'EOF'
---
title: "Example Blogger Auto Poster Post"
labels:
- Example
- Blogger
- Automation
---

# Example Blogger Auto Poster Post

This is a neutral example post for testing the Blogger Auto Poster workflow.

Move this file out of `posts/queue/` or keep `posting.dry_run: true` until your
Google OAuth credentials, blog ID, labels, and posting mode are configured.
EOF

cat > "$TARGET_DIR/posts/order.txt" <<'EOF'
example-post.md
EOF

cat > "$TARGET_DIR/.gitignore" <<'EOF'
__pycache__/
*.pyc
.DS_Store
.venv/

# Real credentials stay local.
config/config.yml
config/config.yml*
client_secret_*.json
credentials.json
credentials.*
blogger-oauth-token.json
pushover_credentials.txt

# Runtime state and reports.
posts/state.json
posts/last-blogger-test-result.json
posts/last-pushover-test-result.json
EOF

cat > "$TARGET_DIR/.gitattributes" <<'EOF'
* text=auto eol=lf
*.sh text eol=lf
*.py text eol=lf
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
Dockerfile text eol=lf
EOF

section "Step 4/6: initializing git repository"
(
  cd "$TARGET_DIR"
  git init -b main
  git add .
  git commit -m "$COMMIT_MESSAGE"
  if [ -n "$REMOTE_URL" ]; then
    git remote add origin "$REMOTE_URL"
  fi
)

section "Step 5/6: export summary"
(
  cd "$TARGET_DIR"
  say "Tracked files:"
  git ls-files | sed 's/^/  /'
  say ""
  say "Tracked posts:"
  git ls-files 'posts/**' | sed 's/^/  /'
  say ""
  say "Current commit:"
  git log -1 --oneline
  say ""
  if [ "$PUSH_REMOTE" -eq 1 ]; then
    if [ -z "$REMOTE_URL" ]; then
      echo "--push requires --remote URL" >&2
      exit 1
    fi
    say "Push target:"
    git remote -v
  else
    say "Push skipped. Run this from the export directory when ready:"
    say "  git push -u origin main"
  fi
)

section "Step 6/6: optional push"
if [ "$PUSH_REMOTE" -eq 1 ]; then
  (
    cd "$TARGET_DIR"
    git push -u origin main
  )
else
  say "No push requested."
fi

section "Result"
say "Public export created: $TARGET_DIR"
say "Only the allowlisted tool files and one neutral example post were exported."
