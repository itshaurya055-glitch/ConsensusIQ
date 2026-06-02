import sqlite3

connection = sqlite3.connect("market_news.db")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS news(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    url TEXT UNIQUE
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