#!/bin/sh
set -eu

PROJECT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$PROJECT_DIR/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"

say() {
  printf '%s\n' "$*"
}

fail() {
  say ""
  say "RESULT: FAILED" >&2
  say "Reason: $*" >&2
  exit 1
}

run_step() {
  label="$1"
  shift
  say "$label"
  if ! "$@"; then
    fail "$label failed."
  fi
}

say "Blogger Auto Poster venv update"
say "Project: $PROJECT_DIR"
say "Python:  $PYTHON_BIN"
say "Venv:    $VENV_DIR"
say ""

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  fail "$PYTHON_BIN was not found in PATH."
fi

if [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
  fail "requirements.txt is missing."
fi

run_step "Step 1/5: removing old virtual environment..." rm -rf "$VENV_DIR"
say "OK: old venv removed."

run_step "Step 2/5: creating virtual environment..." "$PYTHON_BIN" -m venv "$VENV_DIR"
say "OK: venv created."

run_step "Step 3/5: upgrading packaging tools..." "$VENV_DIR/bin/python" -m pip install --upgrade pip setuptools wheel
say "OK: packaging tools updated."

run_step "Step 4/5: installing project requirements..." "$VENV_DIR/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
say "OK: requirements installed."

say "Step 5/5: checking local Python entrypoints..."
if ! "$VENV_DIR/bin/python" -m py_compile src/*.py scripts/manage-posts.py scripts/diagnose-oauth-config.py; then
  fail "Python syntax check failed."
fi
if ! "$VENV_DIR/bin/python" -m src.blogger_auto_poster --help >/dev/null; then
  fail "src.blogger_auto_poster entrypoint check failed."
fi
if ! "$VENV_DIR/bin/python" -m src.prepare_posts --help >/dev/null; then
  fail "src.prepare_posts entrypoint check failed."
fi
if ! "$VENV_DIR/bin/python" scripts/manage-posts.py --help >/dev/null; then
  fail "scripts/manage-posts.py entrypoint check failed."
fi
say "OK: Python entrypoints are usable."

say ""
say "RESULT: OK"
say "To activate this venv in your current shell, run either:"
say "  . .venv/bin/activate"
say "  . scripts/load-venv.sh"
say ""
say "Without activation, run tools explicitly with:"
say "  .venv/bin/python -m src.blogger_auto_poster --help"
