import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_update_delete(tmp_path):
    db_path = tmp_path / "test_watch.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        assert db.get_all() == []

        db.add_series("Test Show", 1)
        rows = db.get_all()
        assert len(rows) == 1
        series_id, title, last = rows[0]
        assert title == "Test Show"
        assert last == 1

        db.update_last_watched(series_id, 5)
        rows = db.get_all()
        assert rows[0][2] == 5

        db.delete_series(series_id)
        assert db.get_all() == []
    finally:
        db.close()
