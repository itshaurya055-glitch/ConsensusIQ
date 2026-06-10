"""
pipeline.py
-----------
Full AI-herding pipeline optimized for Render:
  1. Fetch market news via Tavily
  2. Filter for quality articles
  3. Run LLM to simulate 4 AI agents in a single API call (combined prompt)
  4. Run article analysis concurrently in a thread pool (ThreadPoolExecutor)
  5. Compute weighted herd score and persist results to SQLite
  6. Save a market snapshot with live NIFTY price
"""

import logging
from datetime import datetime
import concurrent.futures

from src.news_collector import fetch_market_news
from src.groq_agent import analyze_news_multi_agent
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
# ARTICLE WORKER
# ─────────────────────────────────────────

def process_single_article(article) -> float | None:
    """Process a single article: call multi-agent LLM and save results to DB."""
    title   = article.get("title", "")
    content = article.get("content", "")
    url     = article.get("url", "")

    # 1. Save news article
    try:
        save_news(title, content, url)
    except Exception as exc:
        logger.warning("[Pipeline] save_news failed for '%s': %s", title[:50], exc)

    # 2. Get combined multi-agent analysis from Groq (1 API call instead of 4)
    try:
        multi_result = analyze_news_multi_agent(title, content)
    except Exception as exc:
        logger.error("[Pipeline] Multi-agent analysis failed for '%s': %s", title[:50], exc)
        return None

    agent_results = []
    
    # 3. Parse and save each agent's signal
    for agent_name in ("conservative", "momentum", "value", "risk_averse"):
        agent_data = multi_result.get(agent_name, {})
        direction  = agent_data.get("direction", "HOLD")
        confidence = agent_data.get("confidence", 50)
        sector     = agent_data.get("sector", "UNKNOWN")
        event_type = agent_data.get("event_type", "UNKNOWN")
        impact     = agent_data.get("impact", "LOW")

        try:
            save_agent_signal(
                article_title=title,
                agent_name=agent_name,
                direction=direction,
                confidence=confidence,
                sector=sector,
                event_type=event_type,
                impact=impact
            )
            agent_results.append({
                "direction":  direction,
                "confidence": confidence
            })
            
            # Save to main signals table using first agent's metadata
            if agent_name == "conservative":
                save_signal(
                    title=title,
                    direction=direction,
                    confidence=confidence,
                    sector=sector,
                    event_type=event_type,
                    impact=impact
                )
        except Exception as exc:
            logger.warning("[Pipeline] Save signal failed for %s on '%s': %s", agent_name, title[:50], exc)

    # 4. Calculate herd score for this article
    if agent_results:
        try:
            h_score = calculate_weighted_consensus(agent_results)
            risk    = score_to_risk(h_score)
            save_herd_score(title, h_score, risk)
            logger.info("[Pipeline] Article '%s...' → herd=%.1f %s", title[:50], h_score, risk)
            return h_score
        except Exception as exc:
            logger.warning("[Pipeline] Herd score calc failed: %s", exc)

    return None


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

    # Cap at 5 articles per run to keep within limits and ensure speed
    target_articles = articles[:5]
    all_herd_scores = []
    
    # ── 2. Run in parallel using a ThreadPoolExecutor ──────────────
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(process_single_article, target_articles)
        for score in results:
            if score is not None:
                all_herd_scores.append(score)

    # ── 3. Market snapshot ─────────────────────────────────────────
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
        save_market_snapshot(snapshot_ts, nifty_price, avg_herd, len(target_articles))
    except Exception as exc:
        logger.warning("[Pipeline] save_market_snapshot failed: %s", exc)

    logger.info(
        "[Pipeline] Done. articles=%d avg_herd=%.1f nifty=%.2f",
        len(target_articles), avg_herd, nifty_price
    )

    return {
        "status":             "ok",
        "articles_processed": len(target_articles),
        "avg_herd_score":     avg_herd,
        "nifty_price":        nifty_price,
        "timestamp":          snapshot_ts,
    }
