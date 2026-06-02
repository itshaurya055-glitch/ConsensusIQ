from src.news_collector import fetch_market_news
from src.news_collector import fetch_market_news
from src.groq_agent import analyze_news
from src.database import save_signal




BAD_KEYWORDS = [
    "sensex",
    "nifty",
    "watch",
    "calendar",
    "homepage",
    "market data",
    "stock quotes",
    "live announcements"
]

def filter_articles(results):

    filtered = []

    for article in results:

        title = article.get("title", "").lower()
        content = article.get("content", "")

        if len(content) < 200:
            continue

        if any(word in title for word in BAD_KEYWORDS):
            continue

        filtered.append(article)

    return filtered

news = fetch_market_news()

filtered_news = filter_articles(news)

for article in filtered_news:

    print("\nAnalyzing:")
    print(article["title"])

    signal = analyze_news(
        article["title"],
        article["content"]
    )

    save_signal(
        article["title"],
        signal["direction"],
        signal["confidence"],
        signal["sector"],
        signal["event_type"],
        signal["impact"]
    )

    print("Signal Saved")


news = fetch_market_news()

article = news[0]

print("TITLE:")
print(article["title"])

print("\nAnalyzing...\n")

result = analyze_news(
    article["title"],
    article["content"]
)

print(result)
print("Total articles fetched:", len(news))
print("After filtering:", len(filtered_news))
print(article["title"])