from datetime import datetime, timezone

from app.services.roll_window import get_current_roll_slot_key, is_now_in_roll_window


def test_roll_window_open() -> None:
    config = [{"days": [1], "start": "09:00", "end": "18:00"}]
    now = datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc)  # Tuesday
    assert is_now_in_roll_window(config, now) is True
    assert get_current_roll_slot_key(config, now) == "2026-04-07:0"


def test_roll_window_closed() -> None:
    config = [{"days": [1], "start": "09:00", "end": "18:00"}]
    now = datetime(2026, 4, 7, 20, 0, tzinfo=timezone.utc)
    assert is_now_in_roll_window(config, now) is False
    assert get_current_roll_slot_key(config, now) is None
