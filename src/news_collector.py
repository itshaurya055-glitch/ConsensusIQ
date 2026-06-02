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