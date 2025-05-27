import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_update_series(tmp_path):
    db_path = tmp_path / "watching.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        # Database should initially be empty
        assert db.get_series() == []

        # Add a series and verify it is retrieved
        db.add_series("My Show", "2023-01-01")
        series = db.get_series()
        assert len(series) == 1
        series_id, title, last_watched = series[0]
        assert title == "My Show"
        assert last_watched == "2023-01-01"

        # Update last_watched and verify the change
        db.update_last_watched(series_id, "2023-02-01")
        updated = db.get_series()
        assert updated[0][2] == "2023-02-01"
    finally:
        db.close()
