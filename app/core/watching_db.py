import sqlite3
import json

class WatchingDB:
    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS watching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT CHECK(type IN ('tv','film')) NOT NULL,
            details TEXT,
            last_watched INTEGER
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def get_entries(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, type, details, last_watched FROM watching")
        return cursor.fetchall()

    def add_series(self, title, type_, details, last_watched):
        details_json = json.dumps(details) if not isinstance(details, str) else details
        query = (
            "INSERT INTO watching (title, type, details, last_watched) "
            "VALUES (?, ?, ?, ?)"
        )
        self.conn.execute(query, (title, type_, details_json, last_watched))
        self.conn.commit()

    def update_last_watched(self, entry_id, last_watched):
        query = "UPDATE watching SET last_watched = ? WHERE id = ?"
        self.conn.execute(query, (last_watched, entry_id))
        self.conn.commit()

    def close(self):
        self.conn.close()
