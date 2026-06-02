import sqlite3

conn = sqlite3.connect("market_news.db")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM news")

print(cursor.fetchone())