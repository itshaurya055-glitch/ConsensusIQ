from datetime import datetime

from src.news_collector import (
    fetch_market_news,
    is_useful_article
)

from src.groq_agent import analyze_news
from src.agents import AGENTS

from src.herd_score import (
    calculate_consensus,
    calculate_weighted_consensus
)

from src.market_data import get_nifty_close

from src.database import (
    save_agent_signal,
    save_herd_score,
    save_market_snapshot
)

# Fetch News
news = fetch_market_news()

print("Total articles fetched:", len(news))

# Filter Junk Articles
news = [
    article
    for article in news
    if is_useful_article(article["title"])
]

print("Articles after filtering:", len(news))

# Snapshot Statistics
all_weighted_scores = []
processed_articles = 0

# Process All Articles
for article in news:

    # Skip articles with very little content
    if len(article["content"]) < 100:
        continue

    print("\n" + "=" * 80)
    print("NEWS:")
    print(article["title"])
    print("=" * 80)

    signals = []

    # Run all agents
    for agent_name, prompt in AGENTS.items():

        signal = analyze_news(
            article["title"],
            article["content"],
            prompt
        )

        signals.append(signal)

        # Save Agent Signal
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

    weighted_consensus = (
        calculate_weighted_consensus(signals)
    )

    all_weighted_scores.append(
        weighted_consensus
    )

    processed_articles += 1

    # Risk Classification
    votes = [
        signal["direction"]
        for signal in signals
    ]

    if all(v == "HOLD" for v in votes):
        risk = "LOW"

    elif consensus >= 80:
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

    # Output
    print("\nHERD SCORE:", consensus)

    print(
        "WEIGHTED HERD SCORE:",
        weighted_consensus
    )

    print("RISK LEVEL:", risk)

# =========================
# SAVE ONE MARKET SNAPSHOT
# =========================

if len(all_weighted_scores) > 0:

    avg_weighted_score = (
        sum(all_weighted_scores)
        / len(all_weighted_scores)
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    nifty_price = get_nifty_close()

    save_market_snapshot(
        timestamp,
        nifty_price,
        round(avg_weighted_score, 2),
        processed_articles
    )

    print("\n" + "=" * 80)
    print("MARKET SNAPSHOT SAVED")
    print("NIFTY PRICE:", round(nifty_price, 2))
    print(
        "AVG WEIGHTED SCORE:",
        round(avg_weighted_score, 2)
    )
    print(
        "ARTICLES ANALYZED:",
        processed_articles
    )
    print("=" * 80)

print("\nFinished processing all articles.")