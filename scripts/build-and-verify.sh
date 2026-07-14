#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
SERVICE_NAME="${SERVICE_NAME:-blogger-auto-poster}"
CONFIG_FILE="${CONFIG_FILE:-$PROJECT_DIR/config/config.yml}"

cd "$PROJECT_DIR"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "Missing config file: $CONFIG_FILE" >&2
  echo "Create it with: cp config/config.example.yml config/config.yml" >&2
  exit 1
fi

if [ ! -f "$PROJECT_DIR/credentials.json" ]; then
  echo "Missing credentials file: $PROJECT_DIR/credentials.json" >&2
  echo "Download the Google OAuth client file and save it as credentials.json." >&2
  exit 1
fi

echo "Building Docker image..."
docker-compose build

echo "Starting container..."
docker-compose up -d

echo "Checking container status..."
container_id="$(docker-compose ps -q "$SERVICE_NAME")"
if [ -z "$container_id" ]; then
  echo "Container for service $SERVICE_NAME was not created." >&2
  exit 1
fi

running_state="$(docker inspect -f '{{.State.Running}}' "$container_id")"
if [ "$running_state" != "true" ]; then
  echo "Container $container_id is not running." >&2
  docker-compose logs --tail=80 "$SERVICE_NAME" >&2
  exit 1
fi

echo "Running safe container dry-run..."
docker-compose exec -T "$SERVICE_NAME" \
  python -m src.blogger_auto_poster --config /config/config.yml --once --log-level INFO

if [ "${VERIFY_BLOGGER_DRAFT:-0}" = "1" ]; then
  echo "Running Blogger draft create/delete verification..."
  docker-compose exec -T "$SERVICE_NAME" \
    python -m src.blogger_auto_poster \
      --config /config/config.yml \
      --verify-blogger-draft-cycle \
      --log-level INFO
else
  echo "Skipping Blogger draft create/delete verification."
  echo "Set VERIFY_BLOGGER_DRAFT=1 to create one test draft and delete it again."
fi

echo "Verification completed."
