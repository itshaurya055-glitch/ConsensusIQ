import sqlite3

conn = sqlite3.connect("market_news.db")
cursor = conn.cursor()

cursor.execute(
    """
    SELECT *
    FROM herd_scores
    """
)

for row in cursor.fetchall():
    print(row)