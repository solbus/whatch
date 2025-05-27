import sqlite3
import json

class WatchingDB:
    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            data TEXT NOT NULL
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def add_series(self, info: dict):
        """Store series info as a JSON string."""
        json_data = json.dumps(info)
        query = "INSERT INTO series (title, data) VALUES (?, ?)"
        self.conn.execute(query, (info.get("title"), json_data))
        self.conn.commit()

    def get_series(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, data FROM series")
        result = []
        for row in cursor.fetchall():
            series_id, title, data = row
            result.append((series_id, title, json.loads(data)))
        return result

    def reset_database(self):
        self.conn.close()
        import os
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.create_table()

    def close(self):
        self.conn.close()
