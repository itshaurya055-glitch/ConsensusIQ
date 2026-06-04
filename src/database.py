import sqlite3

connection = sqlite3.connect("market_news.db")

cursor = connection.cursor()

# NEWS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS news(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    url TEXT UNIQUE
)
""")

# SIGNALS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS signals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    direction TEXT,
    confidence INTEGER,
    sector TEXT,
    event_type TEXT,
    impact TEXT
)
""")

# AGENT SIGNALS TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS agent_signals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_title TEXT,
    agent_name TEXT,
    direction TEXT,
    confidence INTEGER,
    sector TEXT,
    event_type TEXT,
    impact TEXT
)
""")

# HERD SCORES TABLE

cursor.execute("""
CREATE TABLE IF NOT EXISTS herd_scores(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_title TEXT,
    herd_score REAL,
    risk_level TEXT
)
""")

connection.commit()

print("database.py loaded")
connection.commit()

def save_news(title, content, url):

    cursor.execute(
        """
        INSERT OR IGNORE INTO news(title, content, url)
        VALUES (?, ?, ?)
        """,
        (title, content, url)
    )

    connection.commit()
def save_signal(
    title,
    direction,
    confidence,
    sector,
    event_type,
    impact
):

    cursor.execute(
        """
        INSERT INTO signals(
            title,
            direction,
            confidence,
            sector,
            event_type,
            impact
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            direction,
            confidence,
            sector,
            event_type,
            impact
        )
    )

    connection.commit() 
    
def save_herd_score(
    article_title,
    herd_score,
    risk_level
):

    cursor.execute(
        """
        INSERT INTO herd_scores(
            article_title,
            herd_score,
            risk_level
        )
        VALUES (?, ?, ?)
        """,
        (
            article_title,
            herd_score,
            risk_level
        )
    )

    connection.commit()

def save_agent_signal(
    article_title,
    agent_name,
    direction,
    confidence,
    sector,
    event_type,
    impact
):
    cursor.execute(
        """
        INSERT INTO agent_signals(
            article_title,
            agent_name,
            direction,
            confidence,
            sector,
            event_type,
            impact
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            article_title,
            agent_name,
            direction,
            confidence,
            sector,
            event_type,
            impact
        )
    )

    connection.commit()