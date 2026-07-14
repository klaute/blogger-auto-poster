#!/bin/sh

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  printf '%s\n' "Missing venv: $VENV_DIR"
  printf '%s\n' "Run first: scripts/update-venv.sh"
  return 1 2>/dev/null || exit 1
fi

# This file is meant to be sourced:
#   . scripts/load-venv.sh
. "$VENV_DIR/bin/activate"
printf '%s\n' "Loaded venv: $VENV_DIR"
