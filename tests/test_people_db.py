import sys
from pathlib import Path

# Ensure repository root is on sys.path so we import local app package
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.people_db import PeopleDB


def test_add_retrieve_delete(tmp_path):
    db_path = tmp_path / "test.db"
    db = PeopleDB(db_path=str(db_path))
    try:
        # Initially database should be empty
        assert db.get_people() == []

        # Add a person
        db.add_person("Alice", "1990-01-01")
        people = db.get_people()
        assert len(people) == 1
        person_id, name, birthday = people[0]
        assert name == "Alice"
        assert birthday == "1990-01-01"

        # Delete the person and ensure database is empty again
        db.delete_person(person_id)
        assert db.get_people() == []
    finally:
        db.close()


def test_add_series_update_progress(tmp_path):
    db_path = tmp_path / "test.db"
    db = PeopleDB(db_path=str(db_path))
    try:
        # Initially watching table should be empty
        assert db.get_watching() == []

        # Add a series
        db.add_series("Test Show")
        shows = db.get_watching()
        assert len(shows) == 1
        show_id, title, progress = shows[0]
        assert title == "Test Show"
        assert progress == 0

        # Update progress
        db.update_progress(show_id, 5)
        updated = db.get_watching()[0]
        assert updated[2] == 5

        # Delete the series and ensure table is empty again
        db.delete_series(show_id)
        assert db.get_watching() == []
    finally:
        db.close()
