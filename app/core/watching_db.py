import sqlite3


class WatchingDB:
    """Database helper for items the user is currently watching."""

    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS watching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            progress TEXT NOT NULL
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, title, type, progress FROM watching")
        return cursor.fetchall()

    def add_item(self, title, type_, progress="0"):
        query = "INSERT INTO watching (title, type, progress) VALUES (?, ?, ?)"
        self.conn.execute(query, (title, type_, progress))
        self.conn.commit()

    def update_progress(self, item_id, progress):
        query = "UPDATE watching SET progress = ? WHERE id = ?"
        self.conn.execute(query, (progress, item_id))
        self.conn.commit()

    def close(self):
        self.conn.close()
