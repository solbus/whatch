import sqlite3
from datetime import datetime


class LibraryDB:
    """Database helper for the media library."""

    def __init__(self, db_path="whatch.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS library_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL UNIQUE,
            media_type TEXT NOT NULL,
            display_title TEXT NOT NULL,
            is_series INTEGER DEFAULT 0,
            series_title TEXT,
            show_title TEXT,
            added_at TEXT NOT NULL,
            watched INTEGER DEFAULT 0,
            is_placeholder INTEGER DEFAULT 0,
            air_datetime TEXT,
            currently_airing INTEGER DEFAULT 0
        );
        """
        self.conn.execute(query)
        self.conn.commit()

        cursor = self.conn.execute("PRAGMA table_info(library_items)")
        columns = [row[1] for row in cursor.fetchall()]
        if "watched" not in columns:
            self.conn.execute("ALTER TABLE library_items ADD COLUMN watched INTEGER DEFAULT 0")
            self.conn.commit()
        if "is_placeholder" not in columns:
            self.conn.execute("ALTER TABLE library_items ADD COLUMN is_placeholder INTEGER DEFAULT 0")
            self.conn.commit()
        if "air_datetime" not in columns:
            self.conn.execute("ALTER TABLE library_items ADD COLUMN air_datetime TEXT")
            self.conn.commit()
        if "currently_airing" not in columns:
            self.conn.execute("ALTER TABLE library_items ADD COLUMN currently_airing INTEGER DEFAULT 0")
            self.conn.commit()

    def get_items(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT id, path, media_type, display_title, is_series, series_title, show_title, added_at, watched,
                   is_placeholder, air_datetime, currently_airing
            FROM library_items
            """
        )
        return cursor.fetchall()

    def add_item(
        self,
        path,
        media_type,
        display_title,
        is_series=False,
        series_title=None,
        show_title=None,
        is_placeholder=False,
        air_datetime=None,
        currently_airing=0,
    ):
        query = """
        INSERT OR IGNORE INTO library_items
        (path, media_type, display_title, is_series, series_title, show_title, added_at, watched, is_placeholder,
         air_datetime, currently_airing)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        added_at = datetime.utcnow().isoformat(timespec="seconds")
        self.conn.execute(
            query,
            (
                path,
                media_type,
                display_title,
                1 if is_series else 0,
                series_title,
                show_title,
                added_at,
                0,
                1 if is_placeholder else 0,
                air_datetime,
                1 if currently_airing else 0,
            ),
        )
        self.conn.commit()

    def update_watched(self, paths, watched):
        if not paths:
            return
        placeholders = ",".join("?" for _ in paths)
        query = f"UPDATE library_items SET watched = ? WHERE path IN ({placeholders})"
        self.conn.execute(query, (1 if watched else 0, *paths))
        self.conn.commit()

    def update_items(self, items):
        if not items:
            return
        query = """
        UPDATE library_items
        SET media_type = ?, display_title = ?, is_series = ?, series_title = ?, show_title = ?, air_datetime = ?
        WHERE path = ?
        """
        payload = []
        for item in items:
            payload.append(
                (
                    item["media_type"],
                    item["display_title"],
                    1 if item.get("is_series") else 0,
                    item.get("series_title"),
                    item.get("show_title"),
                    item.get("air_datetime"),
                    item["path"],
                )
            )
        self.conn.executemany(query, payload)
        self.conn.commit()

    def assign_placeholder(self, placeholder_path, new_path):
        query = """
        UPDATE library_items
        SET path = ?, is_placeholder = 0
        WHERE path = ?
        """
        self.conn.execute(query, (new_path, placeholder_path))
        self.conn.commit()

    def update_currently_airing(self, series_title, media_type, currently_airing):
        if not series_title:
            return
        query = """
        UPDATE library_items
        SET currently_airing = ?
        WHERE series_title = ? AND media_type = ? AND is_series = 1
        """
        self.conn.execute(query, (1 if currently_airing else 0, series_title, media_type))
        self.conn.commit()

    def delete_by_paths(self, paths):
        if not paths:
            return
        placeholders = ",".join("?" for _ in paths)
        query = f"DELETE FROM library_items WHERE path IN ({placeholders})"
        self.conn.execute(query, tuple(paths))
        self.conn.commit()

    def close(self):
        self.conn.close()
