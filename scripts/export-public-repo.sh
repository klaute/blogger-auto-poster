#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="$(cd "$SOURCE_DIR/.." && pwd)/blogger-auto-poster-public"
REMOTE_URL=""
PUSH_REMOTE=0
FORCE=0

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

if [ -e "$TARGET_DIR" ]; then
  if [ "$FORCE" -ne 1 ]; then
    echo "Target already exists: $TARGET_DIR" >&2
    echo "Use --force to replace it." >&2
    exit 1
  fi
  rm -rf "$TARGET_DIR"
fi

mkdir -p "$TARGET_DIR"

copy_path() {
  local rel_path="$1"
  mkdir -p "$TARGET_DIR/$(dirname "$rel_path")"
  cp -R "$SOURCE_DIR/$rel_path" "$TARGET_DIR/$rel_path"
}

copy_path Dockerfile
copy_path docker-compose.yml
copy_path requirements.txt
copy_path README.md
copy_path config/config.example.yml
copy_path src
copy_path scripts/build-and-verify.sh
copy_path scripts/diagnose-oauth-config.py
copy_path scripts/extract-refresh-key.py
copy_path scripts/export-public-repo.sh
copy_path scripts/get_blogger_token.py
copy_path scripts/load-venv.sh
copy_path scripts/manage-posts.py
copy_path scripts/test-blogger-config.sh
copy_path scripts/update-venv.sh

mkdir -p "$TARGET_DIR/posts/queue" "$TARGET_DIR/posts/done" "$TARGET_DIR/posts/failed"

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

(
  cd "$TARGET_DIR"
  git init -b main
  git add .
  git commit -m "Initial public Blogger Auto Poster export"
  if [ -n "$REMOTE_URL" ]; then
    git remote add origin "$REMOTE_URL"
  fi
  if [ "$PUSH_REMOTE" -eq 1 ]; then
    if [ -z "$REMOTE_URL" ]; then
      echo "--push requires --remote URL" >&2
      exit 1
    fi
    git push -u origin main
  fi
)

echo "Public export created: $TARGET_DIR"
