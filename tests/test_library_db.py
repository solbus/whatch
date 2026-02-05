import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.library_db import LibraryDB


def test_add_retrieve_delete(tmp_path):
    db_path = tmp_path / "test.db"
    db = LibraryDB(db_path=str(db_path))
    try:
        assert db.get_items() == []

        db.add_item(
            path="C:/media/movies/Test Movie.mkv",
            media_type="Movie",
            display_title="Test Movie",
            is_series=False,
            series_title=None,
            show_title=None,
        )

        items = db.get_items()
        assert len(items) == 1
        row = items[0]
        path = row[1]
        media_type = row[2]
        display_title = row[3]
        is_series = row[4]
        series_title = row[5]
        show_title = row[6]
        added_at = row[7]
        watched = row[8]
        assert path == "C:/media/movies/Test Movie.mkv"
        assert media_type == "Movie"
        assert display_title == "Test Movie"
        assert is_series == 0
        assert series_title is None
        assert show_title is None
        assert added_at
        assert watched == 0

        db.delete_by_paths([path])
        assert db.get_items() == []
    finally:
        db.close()
