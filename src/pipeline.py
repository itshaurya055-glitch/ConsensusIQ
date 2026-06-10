"""
pipeline.py
-----------
Full AI-herding pipeline:
  1. Fetch market news via Tavily
  2. Filter for quality articles
  3. Run 4 AI agents (conservative, momentum, value, risk_averse) via Groq
  4. Compute weighted herd score
  5. Persist everything to SQLite
  6. Save a market snapshot with live NIFTY price
"""

import logging
from datetime import datetime

from src.news_collector import fetch_market_news, is_useful_article
from src.groq_agent import analyze_news
from src.agents import AGENTS
from src.herd_score import calculate_weighted_consensus
from src.database import (
    save_news,
    save_signal,
    save_agent_signal,
    save_herd_score,
    save_market_snapshot,
    get_db,
)
from src.market_data import get_nifty_close

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# ARTICLE FILTER
# ─────────────────────────────────────────

BAD_KEYWORDS = [
    "sensex", "nifty", "watch", "calendar",
    "homepage", "market data", "stock quotes", "live announcements",
]


def _filter_articles(results):
    filtered = []
    seen_urls = set()
    for article in results:
        title   = article.get("title", "").lower()
        content = article.get("content", "")
        url     = article.get("url", "")

        if len(content) < 200:
            continue
        if url in seen_urls:
            continue
        if any(word in title for word in BAD_KEYWORDS):
            continue

        seen_urls.add(url)
        filtered.append(article)
    return filtered


# ─────────────────────────────────────────
# RISK LEVEL HELPER
# ─────────────────────────────────────────

def score_to_risk(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    elif score >= 70:
        return "HIGH"
    elif score >= 55:
        return "MEDIUM"
    else:
        return "LOW"


# ─────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────

def run_pipeline():
    """
    Execute the full data → AI → DB pipeline.
    Returns a summary dict for API responses.
    """
    logger.info("[Pipeline] Starting run at %s", datetime.now().isoformat())

    # ── 1. Fetch news ──────────────────────────────────────────────
    try:
        raw_news = fetch_market_news()
    except Exception as exc:
        logger.error("[Pipeline] News fetch failed: %s", exc)
        return {"status": "error", "stage": "news_fetch", "error": str(exc)}

    articles = _filter_articles(raw_news)
    logger.info("[Pipeline] %d articles after filtering (from %d raw)", len(articles), len(raw_news))

    if not articles:
        logger.warning("[Pipeline] No useful articles found.")
        return {"status": "ok", "articles_processed": 0}

    all_herd_scores = []
    articles_processed = 0

    # ── 2. Per-article: multi-agent analysis ───────────────────────
    for article in articles[:10]:          # cap at 10 per run to save API quota
        title   = article.get("title", "")
        content = article.get("content", "")
        url     = article.get("url", "")

        # Save news article
        try:
            save_news(title, content, url)
        except Exception as exc:
            logger.warning("[Pipeline] save_news failed: %s", exc)

        agent_results = []

        for agent_name, agent_prompt in AGENTS.items():
            try:
                result = analyze_news(title, content, agent_prompt)

                save_agent_signal(
                    article_title=title,
                    agent_name=agent_name,
                    direction=result.get("direction", "HOLD"),
                    confidence=result.get("confidence", 50),
                    sector=result.get("sector", "UNKNOWN"),
                    event_type=result.get("event_type", "UNKNOWN"),
                    impact=result.get("impact", "LOW"),
                )

                agent_results.append({
                    "direction":  result.get("direction", "HOLD"),
                    "confidence": result.get("confidence", 50),
                })

                # Save to signals table using first agent's sector/event_type
                if agent_name == "conservative":
                    save_signal(
                        title=title,
                        direction=result.get("direction", "HOLD"),
                        confidence=result.get("confidence", 50),
                        sector=result.get("sector", "UNKNOWN"),
                        event_type=result.get("event_type", "UNKNOWN"),
                        impact=result.get("impact", "LOW"),
                    )

            except Exception as exc:
                logger.warning("[Pipeline] Agent %s failed on '%s': %s", agent_name, title[:60], exc)

        # ── 3. Compute herd score for this article ─────────────────
        if agent_results:
            try:
                h_score = calculate_weighted_consensus(agent_results)
                risk    = score_to_risk(h_score)
                save_herd_score(title, h_score, risk)
                all_herd_scores.append(h_score)
                logger.info("[Pipeline] Article '%s...' → herd=%.1f %s", title[:50], h_score, risk)
            except Exception as exc:
                logger.warning("[Pipeline] Herd score calc failed: %s", exc)

        articles_processed += 1

    # ── 4. Market snapshot ─────────────────────────────────────────
    avg_herd = round(sum(all_herd_scores) / len(all_herd_scores), 2) if all_herd_scores else 0.0

    try:
        nifty_price = get_nifty_close()
    except Exception as exc:
        logger.warning("[Pipeline] NIFTY fetch failed: %s", exc)
        # Use last known price from DB as fallback
        try:
            conn = get_db()
            row  = conn.execute(
                "SELECT nifty_price FROM market_snapshots ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            conn.close()
            nifty_price = float(row["nifty_price"]) if row else 0.0
        except Exception:
            nifty_price = 0.0

    snapshot_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        save_market_snapshot(snapshot_ts, nifty_price, avg_herd, articles_processed)
    except Exception as exc:
        logger.warning("[Pipeline] save_market_snapshot failed: %s", exc)

    logger.info(
        "[Pipeline] Done. articles=%d avg_herd=%.1f nifty=%.2f",
        articles_processed, avg_herd, nifty_price
    )

    return {
        "status":             "ok",
        "articles_processed": articles_processed,
        "avg_herd_score":     avg_herd,
        "nifty_price":        nifty_price,
        "timestamp":          snapshot_ts,
    }
