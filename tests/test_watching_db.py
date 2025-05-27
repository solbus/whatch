import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_get_update(tmp_path):
    db_path = tmp_path / "test_watch.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        assert db.get_items() == []
        db.add_item("Show", "Series", "1")
        items = db.get_items()
        assert len(items) == 1
        item_id, title, type_, progress = items[0]
        assert title == "Show"
        assert type_ == "Series"
        assert progress == "1"
        db.update_progress(item_id, "2")
        assert db.get_items()[0][3] == "2"
    finally:
        db.close()
