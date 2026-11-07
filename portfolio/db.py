import sqlite3
from pathlib import Path
from contextlib import closing
SCHEMA = "CREATE TABLE IF NOT EXISTS experiments (\n id INTEGER PRIMARY KEY, name TEXT NOT NULL,\n a_visitors INTEGER NOT NULL, a_conversions INTEGER NOT NULL,\n b_visitors INTEGER NOT NULL, b_conversions INTEGER NOT NULL, hypothesis TEXT NOT NULL DEFAULT '', primary_metric TEXT NOT NULL DEFAULT '',\n CHECK(a_visitors > 0 AND b_visitors > 0),\n CHECK(a_conversions BETWEEN 0 AND a_visitors),\n CHECK(b_conversions BETWEEN 0 AND b_visitors));"

def connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def initialize(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.executescript(SCHEMA)

def rows(cursor):
    return [dict(row) for row in cursor.fetchall()]
