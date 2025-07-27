"""Simple SQLite database for radio station data."""

import sqlite3
from pathlib import Path

def init_db(db_path: str = "radio_stations.db") -> None:
    """Initialize database with schema."""
    schema_path = Path(__file__).parent / "schema.sql"
    schema_sql = schema_path.read_text()
    
    conn = sqlite3.connect(db_path)
    conn.executescript(schema_sql)
    conn.close()

def get_connection(db_path: str = "radio_stations.db") -> sqlite3.Connection:
    """Get database connection with proper configuration."""
    conn = sqlite3.connect(db_path, autocommit=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn