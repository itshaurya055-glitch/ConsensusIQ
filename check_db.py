import sqlite3

connection = sqlite3.connect("market_news.db")

cursor = connection.cursor()

cursor.execute("SELECT COUNT(*) FROM news")

print(cursor.fetchone())