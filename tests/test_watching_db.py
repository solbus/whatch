import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_and_update(tmp_path):
    db_path = tmp_path / "test_watch.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        assert db.get_items() == []

        db.add_item("Example Show", "TV", "S1E1")
        items = db.get_items()
        assert len(items) == 1
        item_id, title, type_, progress = items[0]
        assert title == "Example Show"
        assert type_ == "TV"
        assert progress == "S1E1"

        db.update_progress(item_id, "S1E2")
        updated = db.get_items()[0]
        assert updated[3] == "S1E2"
    finally:
        db.close()
