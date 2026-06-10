import sqlite3

conn = sqlite3.connect("market_news.db")
cursor = conn.cursor()

cursor.execute("""
SELECT
    timestamp,
    nifty_price,
    avg_weighted_score
FROM market_snapshots
ORDER BY timestamp
""")

rows = cursor.fetchall()

for row in rows:
    print(row)