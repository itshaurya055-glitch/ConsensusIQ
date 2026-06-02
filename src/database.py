import sqlite3

connection = sqlite3.connect("market_news.db")

cursor = connection.cursor()

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