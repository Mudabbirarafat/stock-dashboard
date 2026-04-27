"""
Database initialization and connection helpers.
Uses SQLite for simplicity — swap to PostgreSQL by changing the connection string.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.db")


def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Create tables if they don't already exist."""
    conn = get_db_connection()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            symbol  TEXT PRIMARY KEY,
            name    TEXT NOT NULL,
            sector  TEXT
        );

        CREATE TABLE IF NOT EXISTS stock_data (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol          TEXT NOT NULL,
            date            TEXT NOT NULL,
            open            REAL,
            high            REAL,
            low             REAL,
            close           REAL,
            volume          INTEGER,
            daily_return    REAL,
            moving_avg_7    REAL,
            volatility_score REAL,
            UNIQUE(symbol, date)
        );

        CREATE INDEX IF NOT EXISTS idx_stock_symbol_date
            ON stock_data(symbol, date);
        """
    )
    conn.commit()
    conn.close()
    print("[DB] Tables initialized.")
