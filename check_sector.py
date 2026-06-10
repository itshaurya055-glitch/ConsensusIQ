import sqlite3

conn = sqlite3.connect("market_news.db")
cursor = conn.cursor()

cursor.execute("""
SELECT sector, direction
FROM agent_signals
""")

rows = cursor.fetchall()

sector_votes = {}

for sector, direction in rows:

    if sector not in sector_votes:
        sector_votes[sector] = {}

    sector_votes[sector][direction] = (
        sector_votes[sector].get(direction, 0) + 1
    )

print("\nSECTOR HERDING\n")

for sector, votes in sector_votes.items():

    total = sum(votes.values())

    herd_score = (
        max(votes.values()) / total
    ) * 100

    print(
        sector,
        "→",
        round(herd_score, 2)
    )