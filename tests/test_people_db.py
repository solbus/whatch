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
