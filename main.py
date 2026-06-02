from src.news_collector import fetch_market_news
from src.database import save_news
from src.news_collector import fetch_market_news
from src.groq_agent import analyze_news




BAD_KEYWORDS = [
    "calendar",
    "watch list",
    "market live",
    "dashboard",
    "latest news",
    "share market today",
    "pulse by zerodha"
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

    save_news(
        article.get("title"),
        article.get("content"),
        article.get("url")
    )

    print("Saved:", article.get("title"))

    print("=" * 80)

    print("TITLE:")
    print(article.get("title"))

    print("\nURL:")
    print(article.get("url"))

    print("\nCONTENT:")
    print(article.get("content"))

    print()



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