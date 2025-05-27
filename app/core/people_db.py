import sqlite3

class PeopleDB:
    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        people_query = """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birthday TEXT
            -- You can add more columns (e.g. email, preferences, etc.) as needed.
        );
        """
        self.conn.execute(people_query)

        watching_query = """
        CREATE TABLE IF NOT EXISTS watching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series TEXT NOT NULL,
            progress INTEGER DEFAULT 0
        );
        """
        self.conn.execute(watching_query)
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

    def get_watching(self):
        """Return a list of (id, series, progress) tuples."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, series, progress FROM watching")
        return cursor.fetchall()

    def add_series(self, series, progress=0):
        query = "INSERT INTO watching (series, progress) VALUES (?, ?)"
        self.conn.execute(query, (series, progress))
        self.conn.commit()

    def update_progress(self, series_id, progress):
        query = "UPDATE watching SET progress = ? WHERE id = ?"
        self.conn.execute(query, (progress, series_id))
        self.conn.commit()

    def delete_series(self, series_id):
        query = "DELETE FROM watching WHERE id = ?"
        self.conn.execute(query, (series_id,))
        self.conn.commit()

    def reset_database(self):
        """Delete all data and recreate the people and watching tables."""
        self.conn.close()
        import os
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()

    def close(self):
        self.conn.close()
