from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml

from src.config import load_config
from src.markdown_posts import (
    PostDocument,
    combine_labels,
    first_heading,
    normalize_labels,
    parse_frontmatter,
    should_ignore,
)


def normalize_markdown_body(body: str) -> str:
    lines = [line.rstrip() for line in body.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    normalized: list[str] = []
    previous_blank = True

    for line in lines:
        is_heading = bool(re.match(r"^#{1,6}\s+", line))
        if is_heading and normalized and normalized[-1] != "":
            normalized.append("")
        if line == "":
            if not previous_blank:
                normalized.append(line)
            previous_blank = True
            continue
        normalized.append(line)
        previous_blank = False

    while normalized and normalized[-1] == "":
        normalized.pop()
    return "\n".join(normalized) + "\n"


def frontmatter_text(meta: dict[str, Any]) -> str:
    return yaml.safe_dump(meta, allow_unicode=False, sort_keys=False).strip()


def prepare_file(path: Path, config: dict[str, Any]) -> bool:
    original = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(original)
    body = normalize_markdown_body(body)
    title = str(meta.get("title") or first_heading(body, path.stem)).strip()
    existing_labels = normalize_labels(meta.get("labels") or [])
    probe = PostDocument(
        path=path,
        title=title,
        labels=existing_labels,
        body=body,
    )
    labels = combine_labels(probe, config)
    new_meta = {
        "title": title,
        "labels": labels,
    }
    rendered = f"---\n{frontmatter_text(new_meta)}\n---\n\n{body}"
    if rendered == original:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def iter_targets(input_dir: Path, config: dict[str, Any]) -> list[Path]:
    posting = config.get("posting", {})
    ignore_dirs = set(posting.get("ignore_dirs") or [])
    skip_files = set(posting.get("skip_files") or [])
    return [
        path
        for path in sorted(input_dir.glob("**/*.md"))
        if path.is_file() and not should_ignore(path, input_dir, ignore_dirs, skip_files)
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.example.yml")
    parser.add_argument("--input-dir", default="posts/queue")
    args = parser.parse_args()

    config = load_config(Path(args.config))
    input_dir = Path(args.input_dir)
    changed = 0
    for path in iter_targets(input_dir, config):
        if prepare_file(path, config):
            changed += 1
            print(f"prepared {path}")
    print(f"prepared_files={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
