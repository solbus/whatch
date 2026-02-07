import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.list_db import ListDB


def test_add_retrieve_update_link_and_delete(tmp_path):
    db_path = tmp_path / "test.db"
    db = ListDB(db_path=str(db_path))
    try:
        assert db.get_items() == []

        item_id = db.add_item("TV", "Severance")
        rows = db.get_items()
        assert len(rows) == 1
        row = rows[0]
        assert row[0] == item_id
        assert row[1] == "TV"
        assert row[2] == "Severance"
        assert row[3] is None
        assert row[4] is None
        assert row[5]
        assert row[6] == 0

        db.update_items(
            [
                {
                    "id": item_id,
                    "media_type": "TV",
                    "title": "Severance (2022)",
                    "added_by_person_id": None,
                    "added_at": row[5],
                    "library_linked": 0,
                }
            ]
        )
        updated = db.get_items()[0]
        assert updated[2] == "Severance (2022)"
        assert updated[6] == 0

        db.set_library_linked([item_id], True)
        linked = db.get_items()[0]
        assert linked[6] == 1

        db.delete_by_ids([item_id])
        assert db.get_items() == []
    finally:
        db.close()
