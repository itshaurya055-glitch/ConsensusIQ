from src.news_collector import fetch_market_news
from src.groq_agent import analyze_news
from src.agents import AGENTS
from src.herd_score import calculate_consensus

from src.database import (
    save_agent_signal,
    save_herd_score
)

news = fetch_market_news()

article = news[0]

print("NEWS:")
print(article["title"])

print("\n" + "=" * 60)

signals = []

for agent_name, prompt in AGENTS.items():

    signal = analyze_news(
        article["title"],
        article["content"],
        prompt
    )

    signals.append(signal)

    # Save agent signal
    save_agent_signal(
        article["title"],
        agent_name,
        signal["direction"],
        signal["confidence"],
        signal["sector"],
        signal["event_type"],
        signal["impact"]
    )

    print(agent_name.upper())
    print(signal)

    print("-" * 60)

# Calculate Herd Score
consensus = calculate_consensus(signals)

# Risk Classification
if consensus >= 80:
    risk = "HIGH"

elif consensus >= 60:
    risk = "MEDIUM"

else:
    risk = "LOW"

# Save Herd Score
save_herd_score(
    article["title"],
    consensus,
    risk
)

print("\n" + "=" * 60)
print("HERD SCORE:", consensus)
print("RISK LEVEL:", risk)