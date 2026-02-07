import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ui.library_utils import (  # noqa: E402
    _build_show_air_notes,
    _format_air_datetime_display,
    _format_last_aired_dates,
)


def _tv_placeholder(show_title, air_datetime):
    return (
        1,
        "__placeholder__",
        "TV",
        "S01E01",
        1,
        show_title,
        "1.1",
        "",
        0,
        1,
        air_datetime,
        0,
    )


def test_format_air_datetime_display_uses_dd_mmm_yyyy_and_24h():
    air_dt = datetime(2026, 2, 5, 20, 0)
    assert _format_air_datetime_display(air_dt) == "05-Feb-2026 20:00"


def test_format_last_aired_dates_two_dates_hides_older_year_when_same_year():
    older = datetime(2026, 1, 3, 20, 0)
    newer = datetime(2026, 2, 5, 20, 0)
    assert _format_last_aired_dates([older, newer]) == "03-Jan & 05-Feb-2026"


def test_format_last_aired_dates_two_dates_shows_older_year_when_different_year():
    older = datetime(2025, 12, 20, 20, 0)
    newer = datetime(2026, 1, 10, 20, 0)
    assert _format_last_aired_dates([older, newer]) == "20-Dec-2025 & 10-Jan-2026"


def test_format_last_aired_dates_three_dates_applies_per_pair_year_rules():
    older = datetime(2025, 12, 20, 20, 0)
    newer = datetime(2026, 1, 10, 20, 0)
    newest = datetime(2026, 2, 5, 20, 0)
    assert _format_last_aired_dates([older, newer, newest]) == "20-Dec-2025, 10-Jan, & 05-Feb-2026"


def test_build_show_air_notes_prioritizes_last_aired_when_past_placeholder_exists():
    now = datetime(2026, 2, 6, 12, 0)
    items = [
        _tv_placeholder("The Show", "2026-02-05 20:00"),
        _tv_placeholder("The Show", "2026-02-10 21:00"),
    ]
    notes = _build_show_air_notes(items, now=now)
    assert notes["The Show"] == "Last aired 05-Feb-2026"


def test_build_show_air_notes_uses_next_airs_when_only_future_placeholders_exist():
    now = datetime(2026, 2, 6, 12, 0)
    items = [
        _tv_placeholder("The Show", "2026-02-10 21:00"),
        _tv_placeholder("The Show", "2026-02-17 21:00"),
    ]
    notes = _build_show_air_notes(items, now=now)
    assert notes["The Show"] == "Next airs 10-Feb-2026 21:00"


def test_build_show_air_notes_uses_last_aired_for_past_only():
    now = datetime(2026, 2, 6, 12, 0)
    items = [
        _tv_placeholder("The Show", "2026-02-01 20:00"),
        _tv_placeholder("The Show", "2026-02-05 20:00"),
    ]
    notes = _build_show_air_notes(items, now=now)
    assert notes["The Show"] == "Last aired 01-Feb & 05-Feb-2026"
