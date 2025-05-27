import sys
from pathlib import Path
import json

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.watching_db import WatchingDB


def test_add_series(tmp_path):
    db_path = tmp_path / "test_watch.db"
    db = WatchingDB(db_path=str(db_path))
    try:
        assert db.get_series() == []
        info = {
            "title": "Example Show",
            "type": "TV",
            "seasons": 2,
            "episodes_per_season": [10, 8],
            "average_length": 45,
            "last_watched_episode": "S2E1",
        }
        db.add_series(info)
        series = db.get_series()
        assert len(series) == 1
        _id, title, data = series[0]
        assert title == "Example Show"
        assert data["seasons"] == 2
        assert data["episodes_per_season"] == [10, 8]
    finally:
        db.close()
