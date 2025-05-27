import sys
import json
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_retrieve_update(tmp_path):
    db_path = tmp_path / "test.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        assert db.get_entries() == []

        details = {"season": 1, "episode": 2}
        db.add_series("Example", "tv", details, 100)

        entries = db.get_entries()
        assert len(entries) == 1
        entry_id, title, type_, stored_details, last_watched = entries[0]
        assert title == "Example"
        assert type_ == "tv"
        assert json.loads(stored_details) == details
        assert last_watched == 100

        db.update_last_watched(entry_id, 200)
        updated = db.get_entries()[0]
        assert updated[4] == 200
    finally:
        db.close()

