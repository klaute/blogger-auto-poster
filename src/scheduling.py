from __future__ import annotations

from datetime import datetime, time as datetime_time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
    "montag": 0,
    "dienstag": 1,
    "mittwoch": 2,
    "donnerstag": 3,
    "freitag": 4,
    "samstag": 5,
    "sonntag": 6,
}


def schedule_config(config: dict[str, Any]) -> dict[str, Any]:
    return (config.get("posting") or {}).get("schedule") or {}


def parse_schedule_weekday(value: Any) -> int:
    if isinstance(value, int):
        if 0 <= value <= 6:
            return value
        raise ValueError("schedule.weekday must be 0-6 or a weekday name.")
    key = str(value or "friday").strip().lower()
    if key not in WEEKDAYS:
        raise ValueError(f"Unknown schedule weekday: {value}")
    return WEEKDAYS[key]


def parse_schedule_time(value: Any) -> datetime_time:
    raw = str(value or "09:00").strip()
    parts = raw.split(":")
    if len(parts) not in {2, 3}:
        raise ValueError("schedule.time must use HH:MM or HH:MM:SS.")
    hour = int(parts[0])
    minute = int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return datetime_time(hour=hour, minute=minute, second=second)


def schedule_timezone(config: dict[str, Any]) -> ZoneInfo:
    schedule = schedule_config(config)
    tz_name = str(schedule.get("timezone") or "Europe/Berlin").strip()
    return ZoneInfo(tz_name)


def next_scheduled_datetime(
    config: dict[str, Any],
    slot_index: int = 0,
    now: datetime | None = None,
) -> datetime:
    schedule = schedule_config(config)
    tz = schedule_timezone(config)
    weekday = parse_schedule_weekday(schedule.get("weekday", "friday"))
    publish_time = parse_schedule_time(schedule.get("time", "09:00"))
    now_local = now.astimezone(tz) if now else datetime.now(tz)
    candidate = datetime.combine(now_local.date(), publish_time, tzinfo=tz)
    days_ahead = (weekday - candidate.weekday()) % 7
    candidate = candidate + timedelta(days=days_ahead)
    if candidate <= now_local:
        candidate = candidate + timedelta(days=7)
    return candidate + timedelta(weeks=slot_index)


def next_weekly_due_datetime(config: dict[str, Any], state: dict[str, Any], now: datetime | None = None) -> datetime:
    schedule = schedule_config(config)
    tz = schedule_timezone(config)
    weekday = parse_schedule_weekday(schedule.get("weekday", "friday"))
    publish_time = parse_schedule_time(schedule.get("time", "09:00"))
    now_local = now.astimezone(tz) if now else datetime.now(tz)
    last_post_at = state.get("last_post_at")
    if not last_post_at:
        candidate = datetime.combine(now_local.date(), publish_time, tzinfo=tz)
        return candidate + timedelta(days=(weekday - candidate.weekday()) % 7)
    last_local = datetime.fromisoformat(last_post_at).astimezone(tz)
    candidate = datetime.combine(last_local.date(), publish_time, tzinfo=tz)
    candidate = candidate + timedelta(days=(weekday - candidate.weekday()) % 7)
    if candidate <= last_local:
        candidate = candidate + timedelta(days=7)
    return candidate


def blogger_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def is_due(state: dict[str, Any], interval_seconds: int) -> bool:
    last_post_at = state.get("last_post_at")
    if not last_post_at:
        return True
    last = datetime.fromisoformat(last_post_at)
    elapsed = datetime.now(timezone.utc).timestamp() - last.timestamp()
    return elapsed >= interval_seconds


def seconds_until_due(state: dict[str, Any], interval_seconds: int) -> int:
    last_post_at = state.get("last_post_at")
    if not last_post_at:
        return 0
    last = datetime.fromisoformat(last_post_at)
    elapsed = datetime.now(timezone.utc).timestamp() - last.timestamp()
    return max(0, int(interval_seconds - elapsed))


def posting_due(config: dict[str, Any], state: dict[str, Any], interval_seconds: int) -> bool:
    posting_config = config.get("posting") or {}
    due_mode = str(posting_config.get("due_mode", "interval")).lower()
    if due_mode == "weekly_schedule":
        due_at = next_weekly_due_datetime(config, state)
        return datetime.now(due_at.tzinfo) >= due_at
    return is_due(state, interval_seconds)


def seconds_until_posting_due(config: dict[str, Any], state: dict[str, Any], interval_seconds: int) -> int:
    posting_config = config.get("posting") or {}
    due_mode = str(posting_config.get("due_mode", "interval")).lower()
    if due_mode == "weekly_schedule":
        due_at = next_weekly_due_datetime(config, state)
        return max(0, int((due_at - datetime.now(due_at.tzinfo)).total_seconds()))
    return seconds_until_due(state, interval_seconds)
