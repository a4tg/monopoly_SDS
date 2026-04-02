from __future__ import annotations

from datetime import datetime


def _slot_minutes(slot: dict) -> tuple[int, int] | None:
    try:
        start_h, start_m = [int(x) for x in str(slot.get("start", "")).split(":")]
        end_h, end_m = [int(x) for x in str(slot.get("end", "")).split(":")]
    except Exception:
        return None
    return start_h * 60 + start_m, end_h * 60 + end_m


def is_now_in_roll_window(roll_window_config: list[dict], now: datetime) -> bool:
    if not roll_window_config:
        return False

    weekday = now.weekday()  # 0=Mon
    now_minutes = now.hour * 60 + now.minute

    for slot in roll_window_config:
        days = slot.get("days", [])
        if days and weekday not in days:
            continue

        parsed = _slot_minutes(slot)
        if not parsed:
            continue

        start_minutes, end_minutes = parsed

        if start_minutes <= now_minutes <= end_minutes:
            return True

    return False


def get_current_roll_slot_key(roll_window_config: list[dict], now: datetime) -> str | None:
    weekday = now.weekday()
    now_minutes = now.hour * 60 + now.minute
    date_key = now.strftime("%Y-%m-%d")

    for idx, slot in enumerate(roll_window_config):
        days = slot.get("days", [])
        if days and weekday not in days:
            continue

        parsed = _slot_minutes(slot)
        if not parsed:
            continue
        start_minutes, end_minutes = parsed
        if start_minutes <= now_minutes <= end_minutes:
            return f"{date_key}:{idx}"

    return None
