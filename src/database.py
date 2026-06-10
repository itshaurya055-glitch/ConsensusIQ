import os
import sqlite3
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "market_news.db")


def get_db():
    """Return a fresh thread-safe SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS news(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        url TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS signals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        direction TEXT,
        confidence INTEGER,
        sector TEXT,
        event_type TEXT,
        impact TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS agent_signals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_title TEXT,
        agent_name TEXT,
        direction TEXT,
        confidence INTEGER,
        sector TEXT,
        event_type TEXT,
        impact TEXT,
        timestamp TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS herd_scores(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        article_title TEXT,
        herd_score REAL,
        risk_level TEXT,
        timestamp TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS market_snapshots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT UNIQUE,
        nifty_price REAL,
        avg_weighted_score REAL,
        article_count INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS correlation_results(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        herd_score REAL,
        future_return_pct REAL
    )
    """)

    # Migrate: add created_at to old tables if missing
    for table in ("news", "signals", "agent_signals"):
        col_field = "created_at" if table != "agent_signals" else "timestamp"
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col_field} TEXT DEFAULT (datetime('now','localtime'))")
        except Exception:
            pass  # column already exists

    conn.commit()
    conn.close()
    print("[DB] Initialized successfully.")


# ─────────────────────────────────────────
# SAVE NEWS
# ─────────────────────────────────────────

def save_news(title, content, url):
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO news(title, content, url, created_at)
        VALUES (?, ?, ?, datetime('now','localtime'))
        """,
        (title, content, url)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SAVE SIGNAL
# ─────────────────────────────────────────

def save_signal(title, direction, confidence, sector, event_type, impact):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO signals(title, direction, confidence, sector, event_type, impact, created_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """,
        (title, direction, confidence, sector, event_type, impact)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SAVE AGENT SIGNAL
# ─────────────────────────────────────────

def save_agent_signal(article_title, agent_name, direction, confidence, sector, event_type, impact):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO agent_signals(article_title, agent_name, direction, confidence, sector, event_type, impact, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
        """,
        (article_title, agent_name, direction, confidence, sector, event_type, impact)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SAVE HERD SCORE
# ─────────────────────────────────────────

def save_herd_score(article_title, herd_score, risk_level):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()
    conn.execute(
        """
        INSERT INTO herd_scores(article_title, herd_score, risk_level, timestamp)
        VALUES (?, ?, ?, ?)
        """,
        (article_title, herd_score, risk_level, timestamp)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SAVE MARKET SNAPSHOT
# ─────────────────────────────────────────

def save_market_snapshot(timestamp, nifty_price, avg_weighted_score, article_count):
    conn = get_db()
    conn.execute(
        """
        INSERT OR IGNORE INTO market_snapshots(timestamp, nifty_price, avg_weighted_score, article_count)
        VALUES (?, ?, ?, ?)
        """,
        (timestamp, nifty_price, avg_weighted_score, article_count)
    )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────
# SAVE CORRELATION RESULT
# ─────────────────────────────────────────

def save_correlation_result(timestamp, herd_score, future_return_pct):
    conn = get_db()
    conn.execute(
        """
        INSERT INTO correlation_results(timestamp, herd_score, future_return_pct)
        VALUES (?, ?, ?)
        """,
        (timestamp, herd_score, future_return_pct)
    )
    conn.commit()
    conn.close()