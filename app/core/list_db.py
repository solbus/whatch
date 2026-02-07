import sqlite3
from datetime import datetime


class ListDB:
    """Database helper for watchlist-style entries."""

    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        people_query = """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            birthday TEXT
        );
        """
        self.conn.execute(people_query)

        query = """
        CREATE TABLE IF NOT EXISTS list_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_type TEXT NOT NULL,
            title TEXT NOT NULL,
            added_by_person_id INTEGER,
            added_at TEXT NOT NULL,
            library_linked INTEGER DEFAULT 0
        );
        """
        self.conn.execute(query)
        self.conn.commit()

        cursor = self.conn.execute("PRAGMA table_info(list_items)")
        columns = [row[1] for row in cursor.fetchall()]
        if "added_by_person_id" not in columns:
            self.conn.execute("ALTER TABLE list_items ADD COLUMN added_by_person_id INTEGER")
            self.conn.commit()
        if "added_at" not in columns:
            self.conn.execute("ALTER TABLE list_items ADD COLUMN added_at TEXT")
            now = datetime.utcnow().isoformat(timespec="seconds")
            self.conn.execute("UPDATE list_items SET added_at = COALESCE(added_at, ?)", (now,))
            self.conn.commit()
        if "library_linked" not in columns:
            self.conn.execute("ALTER TABLE list_items ADD COLUMN library_linked INTEGER DEFAULT 0")
            self.conn.commit()

    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT li.id, li.media_type, li.title, li.added_by_person_id, p.name, li.added_at, li.library_linked
            FROM list_items li
            LEFT JOIN people p ON p.id = li.added_by_person_id
            """
        )
        return cursor.fetchall()

    def add_item(self, media_type, title, added_by_person_id=None):
        query = """
        INSERT INTO list_items (media_type, title, added_by_person_id, added_at, library_linked)
        VALUES (?, ?, ?, ?, 0)
        """
        added_at = datetime.utcnow().isoformat(timespec="seconds")
        cursor = self.conn.cursor()
        cursor.execute(query, (media_type, title, added_by_person_id, added_at))
        self.conn.commit()
        return cursor.lastrowid

    def update_items(self, items):
        if not items:
            return
        query = """
        UPDATE list_items
        SET media_type = ?, title = ?, added_by_person_id = ?, added_at = ?, library_linked = ?
        WHERE id = ?
        """
        payload = [
            (
                item["media_type"],
                item["title"],
                item.get("added_by_person_id"),
                item["added_at"],
                1 if item.get("library_linked") else 0,
                item["id"],
            )
            for item in items
        ]
        self.conn.executemany(query, payload)
        self.conn.commit()

    def set_library_linked(self, item_ids, linked):
        if not item_ids:
            return
        placeholders = ",".join("?" for _ in item_ids)
        query = f"UPDATE list_items SET library_linked = ? WHERE id IN ({placeholders})"
        self.conn.execute(query, (1 if linked else 0, *item_ids))
        self.conn.commit()

    def delete_by_ids(self, item_ids):
        if not item_ids:
            return
        placeholders = ",".join("?" for _ in item_ids)
        query = f"DELETE FROM list_items WHERE id IN ({placeholders})"
        self.conn.execute(query, tuple(item_ids))
        self.conn.commit()

    def close(self):
        self.conn.close()
