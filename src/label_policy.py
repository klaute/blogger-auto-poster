from __future__ import annotations

import logging
import re
from typing import Any, Callable

from src.markdown_posts import normalize_labels

LOGGER = logging.getLogger("blogger-auto-poster")


def normalized_label_key(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip()).casefold()


def compact_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip())


def align_labels_with_existing(
    labels: list[str],
    existing_labels: list[str],
) -> tuple[list[str], list[tuple[str, str]], list[str]]:
    existing_by_key = {
        normalized_label_key(label): compact_label(label)
        for label in existing_labels
        if compact_label(label)
    }

    result: list[str] = []
    seen: set[str] = set()
    replacements: list[tuple[str, str]] = []
    new_labels: list[str] = []

    for raw_label in normalize_labels(labels):
        compacted = compact_label(raw_label)
        if not compacted:
            continue
        key = normalized_label_key(compacted)
        final_label = existing_by_key.get(key, compacted)
        if key in seen:
            continue
        if final_label != compacted:
            replacements.append((compacted, final_label))
        elif key not in existing_by_key:
            new_labels.append(final_label)
        result.append(final_label)
        seen.add(key)

    return result, replacements, new_labels


def labels_for_blogger_write(
    config: dict[str, Any],
    labels: list[str],
    list_labels: Callable[[dict[str, Any]], list[str]],
) -> list[str]:
    existing_labels = list_labels(config)
    aligned, replacements, new_labels = align_labels_with_existing(labels, existing_labels)

    if replacements:
        LOGGER.info(
            "Aligned Blogger labels with existing spelling: %s",
            ", ".join(f"{old} -> {new}" for old, new in replacements),
        )
    if new_labels:
        LOGGER.info(
            "Using new Blogger labels not found on the blog yet: %s",
            ", ".join(new_labels),
        )
    return aligned
