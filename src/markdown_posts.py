from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import markdown
import yaml


@dataclass
class PostDocument:
    path: Path
    title: str
    labels: list[str]
    body: str


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw_meta = text[4:end]
    body = text[end + 5 :]
    meta = yaml.safe_load(raw_meta) or {}
    if not isinstance(meta, dict):
        return {}, body
    return meta, body


def first_heading(body: str, fallback: str) -> str:
    for line in body.splitlines():
        match = re.match(r"^#\s+(.+?)\s*$", line)
        if match:
            return match.group(1).strip()
    return fallback


def normalize_labels(labels: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for label in labels:
        if label is None:
            continue
        normalized = str(label).strip()
        if not normalized or normalized in seen:
            continue
        result.append(normalized)
        seen.add(normalized)
    return result


def read_post(path: Path) -> PostDocument:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    title = str(meta.get("title") or first_heading(body, path.stem)).strip()
    labels = normalize_labels(meta.get("labels") or [])
    return PostDocument(
        path=path,
        title=title,
        labels=labels,
        body=body,
    )


def should_ignore(path: Path, input_dir: Path, ignore_dirs: set[str], skip_files: set[str]) -> bool:
    rel_parts = path.relative_to(input_dir).parts
    if path.name in skip_files:
        return True
    return any(part in ignore_dirs for part in rel_parts[:-1])


def sort_by_order_file(files: list[Path], order_file: Path) -> list[Path]:
    if not order_file.exists():
        return sorted(files)
    ordered_names = [
        line.strip()
        for line in order_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    order = {name: index for index, name in enumerate(ordered_names)}
    return sorted(files, key=lambda path: (order.get(path.name, len(order)), path.name))


def iter_markdown_files(config: dict[str, Any]) -> list[Path]:
    posting = config.get("posting", {})
    input_dir = Path(posting.get("input_dir", "/data/queue"))
    scan_recursive = bool(posting.get("scan_recursive", True))
    ignore_dirs = set(posting.get("ignore_dirs") or [])
    skip_files = set(posting.get("skip_files") or [])

    pattern = "**/*.md" if scan_recursive else "*.md"
    files = [
        path
        for path in input_dir.glob(pattern)
        if path.is_file() and not should_ignore(path, input_dir, ignore_dirs, skip_files)
    ]
    order_file = posting.get("order_file")
    if order_file:
        files = sort_by_order_file(files, Path(order_file))
    return files


def combine_labels(post: PostDocument, config: dict[str, Any]) -> list[str]:
    return normalize_labels(post.labels)


def markdown_to_html(post: PostDocument, config: dict[str, Any]) -> str:
    content_config = config.get("content", {})
    extensions = content_config.get("markdown_extensions") or ["extra", "sane_lists"]
    html = markdown.markdown(post.body, extensions=extensions, output_format="html5")
    footer_html = str(content_config.get("footer_html") or "")
    if footer_html:
        html = f"{html}\n{footer_html}"
    return html


def source_id_for_post(post: PostDocument) -> str:
    digest = hashlib.sha256(post.path.name.encode("utf-8")).hexdigest()[:16]
    return f"{post.path.name}:{digest}"


def tracking_marker(config: dict[str, Any], source_id: str) -> str:
    tracking_config = config.get("tracking") or {}
    marker_prefix = str(
        tracking_config.get("marker_prefix") or "blogger-auto-poster-source-id"
    )
    return f"{marker_prefix}: {source_id}"


def add_tracking_marker(html: str, marker: str) -> str:
    return f"<!-- {marker} -->\n{html}"


def content_hash_for_post(post: PostDocument, html: str, labels: list[str]) -> str:
    payload = {
        "title": post.title,
        "labels": labels,
        "html": html,
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
