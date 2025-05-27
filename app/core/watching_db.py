import sqlite3

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
            last_watched INTEGER DEFAULT 0
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def get_all(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, last_watched FROM watching")
        return cursor.fetchall()

    def add_series(self, title, last_watched=0):
        query = "INSERT INTO watching (title, last_watched) VALUES (?, ?)"
        self.conn.execute(query, (title, last_watched))
        self.conn.commit()

    def update_last_watched(self, series_id, last_watched):
        query = "UPDATE watching SET last_watched = ? WHERE id = ?"
        self.conn.execute(query, (last_watched, series_id))
        self.conn.commit()

    def delete_series(self, series_id):
        query = "DELETE FROM watching WHERE id = ?"
        self.conn.execute(query, (series_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
