import sqlite3

class PeopleDB:
    def __init__(self, db_path="whatch.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
            -- You can add more columns (e.g. email, preferences, etc.) as needed.
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def get_people(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name FROM people")
        return cursor.fetchall()

    def add_person(self, name):
        query = "INSERT INTO people (name) VALUES (?)"
        self.conn.execute(query, (name,))
        self.conn.commit()

    def update_person(self, person_id, name):
        query = "UPDATE people SET name = ? WHERE id = ?"
        self.conn.execute(query, (name, person_id))
        self.conn.commit()

    def delete_person(self, person_id):
        query = "DELETE FROM people WHERE id = ?"
        self.conn.execute(query, (person_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
