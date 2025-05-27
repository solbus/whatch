import sqlite3


class WatchingDB:
    """Database helper for the "Currently Watching" list."""

    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        """Create the table used to store currently watching items."""
        query = """
        CREATE TABLE IF NOT EXISTS currently_watching (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            type TEXT NOT NULL,
            progress TEXT
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def get_items(self):
        """Return a list of (id, title, type, progress) tuples."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, title, type, progress FROM currently_watching"
        )
        return cursor.fetchall()

    def add_item(self, title, type_, progress):
        """Insert a new item into the currently watching table."""
        query = (
            "INSERT INTO currently_watching (title, type, progress) VALUES (?, ?, ?)"
        )
        self.conn.execute(query, (title, type_, progress))
        self.conn.commit()

    def update_progress(self, item_id, progress):
        """Update the progress for an item."""
        query = "UPDATE currently_watching SET progress = ? WHERE id = ?"
        self.conn.execute(query, (progress, item_id))
        self.conn.commit()

    def delete_item(self, item_id):
        """Delete an item from the list."""
        query = "DELETE FROM currently_watching WHERE id = ?"
        self.conn.execute(query, (item_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
