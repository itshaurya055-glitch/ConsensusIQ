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

print(
    "\nTimestamp | Herd Score | Future Return %"
)

for i in range(len(rows) - 1):

    current_time = rows[i][0]
    current_price = rows[i][1]
    herd_score = rows[i][2]

    future_price = rows[i + 1][1]

    future_return = (
        (future_price - current_price)
        / current_price
    ) * 100

    from src.database import (
        save_correlation_result
    )

    save_correlation_result(
        current_time,
        herd_score,
        round(future_return, 3)
    )