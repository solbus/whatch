import sqlite3

class PeopleDB:
    def __init__(self, db_path="whatch.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birthday TEXT
            -- You can add more columns (e.g. email, preferences, etc.) as needed.
        );
        """
        self.conn.execute(query)
        self.conn.commit()

        # If the table existed before the birthday column was introduced,
        # ensure the column is present.
        cursor = self.conn.execute("PRAGMA table_info(people)")
        columns = [row[1] for row in cursor.fetchall()]
        if "birthday" not in columns:
            self.conn.execute("ALTER TABLE people ADD COLUMN birthday TEXT")
            self.conn.commit()

    def get_people(self):
        """Return a list of (id, name, birthday) tuples."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, birthday FROM people")
        return cursor.fetchall()

    def add_person(self, name, birthday):
        query = "INSERT INTO people (name, birthday) VALUES (?, ?)"
        self.conn.execute(query, (name, birthday))
        self.conn.commit()

    def update_person(self, person_id, name, birthday):
        query = "UPDATE people SET name = ?, birthday = ? WHERE id = ?"
        self.conn.execute(query, (name, birthday, person_id))
        self.conn.commit()

    def delete_person(self, person_id):
        query = "DELETE FROM people WHERE id = ?"
        self.conn.execute(query, (person_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
