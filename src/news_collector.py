from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("TAVILY_API_KEY")

client = TavilyClient(api_key=api_key)


def fetch_market_news():

    queries = [
    "Indian stock market news today",
    "company earnings today India",
    "RBI announcement today",
    "IPO news India today",
    "market moving news today"
]

    all_results = []

    for query in queries:

        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=5
        )

        all_results.extend(response["results"])

    return all_results

BAD_KEYWORDS = [
    "calendar",
    "dashboard",
    "watch",
    "upcoming ipo",
    "ipo list",
    "earnings calendar",
    "market calendar",
    "press releases",
    "share market live",
    "live market",
    "stock market live",
    "results calendar",
    "quarterly results",
    "corporate filings",
    "ipo dashboard"
]

GOOD_KEYWORDS = [
    "rbi",
    "repo",
    "inflation",
    "interest rate",
    "earnings",
    "quarterly results",
    "market crash",
    "market fall",
    "market rally",
    "ipo news",
    "acquisition",
    "merger",
    "policy",
    "fed",
    "tariff",
    "sanctions"
]

def is_useful_article(title):

    title = title.lower()

    # Step 1: Reject junk
    for keyword in BAD_KEYWORDS:
        if keyword in title:
            return False

    # Step 2: Accept only important news
    for keyword in GOOD_KEYWORDS:
        if keyword in title:
            return True

    return False