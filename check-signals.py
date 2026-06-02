import sqlite3

conn = sqlite3.connect("market_news.db")

cursor = conn.cursor()

cursor.execute(
    "SELECT * FROM signals"
)

rows = cursor.fetchall()

for row in rows:
    print(row)