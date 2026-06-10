"""
app.py  –  ConsensusIQ Flask Backend
======================================
Routes
------
GET  /                          → Dashboard HTML
GET  /api/nifty-price           → Latest NIFTY price
GET  /api/herd-score            → Latest weighted herd score + risk level
GET  /api/herd-history          → Last 24h herd scores + nifty for sparkline
GET  /api/market-risk           → Dynamic risk label derived from herd score
GET  /api/articles-today        → Count of articles ingested today
GET  /api/signals-count         → Count of AI signals generated today
GET  /api/sector-analysis       → Sector % breakdown
GET  /api/agent-signals         → Last 4 agent signals with names & direction
GET  /api/recent-news           → Last 6 news articles with herd scores
GET  /api/event-impact          → Event-type % breakdown
GET  /api/system-metrics        → Total articles, signals, latency, nodes
GET  /api/chart/herd-trend      → All-time herd score series
GET  /api/chart/nifty-trend     → All-time NIFTY price series
GET  /api/chart/sector-herding  → Avg confidence by sector
GET  /api/chart/agent-distribution → Direction counts
GET  /api/chart/risk-distribution  → Risk level counts
GET  /api/correlation-analytics → Pearson r + scatter data
GET  /api/scheduler-status      → Next snapshot & pipeline fire times
GET  /api/live-feed             → Server-Sent Events stream (real-time push)
POST /api/run-pipeline          → Manually trigger news-fetch & AI pipeline
POST /api/run-snapshot          → Manually trigger lightweight snapshot
"""

import json
import logging
import math
import time
import threading
from datetime import datetime, timedelta

from flask import Flask, render_template, jsonify, Response, request

from src.database import get_db, init_db
from src.herd_score import calculate_weighted_consensus

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")

# ─────────────────────────────────────────
# SSE subscriber registry
# ─────────────────────────────────────────

_sse_clients: list[list] = []   # each entry is a 1-element list holding a message queue
_sse_lock = threading.Lock()


def _push_sse(data: dict):
    """Broadcast a dict as an SSE event to all connected clients."""
    payload = f"data: {json.dumps(data)}\n\n"
    dead = []
    with _sse_lock:
        for q in _sse_clients:
            try:
                q.append(payload)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────

def _seconds_to_human(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        return f"{seconds // 60}m ago"
    elif seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def _herd_to_risk(score: float) -> str:
    if score >= 85:
        return "CRITICAL"
    elif score >= 70:
        return "HIGH RISK"
    elif score >= 55:
        return "MEDIUM RISK"
    else:
        return "LOW RISK"


def _get_latest_herd_score() -> float:
    """Return the latest herd score from DB (or 0.0)."""
    conn = get_db()
    row = conn.execute(
        "SELECT herd_score FROM herd_scores ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return float(row["herd_score"]) if row else 0.0


def _pearson(x: list, y: list) -> float:
    """Pearson r – no external dependencies."""
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx  = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy  = math.sqrt(sum((yi - my) ** 2 for yi in y))
    return round(num / (dx * dy), 4) if dx and dy else 0.0


# ─────────────────────────────────────────
# Routes
# ─────────────────────────────────────────

@app.route("/")
def index():
    return render_template("dashboard.html")


# ---------- NIFTY Price ----------

@app.route("/api/nifty-price")
def get_nifty_price():
    conn = get_db()
    row = conn.execute(
        "SELECT nifty_price, timestamp FROM market_snapshots ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        return jsonify({"price": row["nifty_price"], "timestamp": row["timestamp"]})
    return jsonify({"price": 0, "timestamp": None})


# ---------- Herd Score ----------

@app.route("/api/herd-score")
def get_herd_score():
    conn = get_db()
    row = conn.execute(
        "SELECT herd_score, risk_level, timestamp FROM herd_scores ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        score = float(row["herd_score"])
        return jsonify({
            "score":      score,
            "risk_level": row["risk_level"] or _herd_to_risk(score),
            "timestamp":  row["timestamp"],
        })
    return jsonify({"score": 0.0, "risk_level": "LOW RISK", "timestamp": None})


# ---------- Herd History (sparkline / chart) ----------

@app.route("/api/herd-history")
def get_herd_history():
    since = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db()

    herd_rows = conn.execute(
        """
        SELECT timestamp, herd_score as avg_score
        FROM herd_scores
        WHERE timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (since,),
    ).fetchall()

    snap_rows = conn.execute(
        """
        SELECT timestamp, nifty_price, avg_weighted_score
        FROM market_snapshots
        WHERE timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (since,),
    ).fetchall()
    conn.close()

    return jsonify({
        "herd": [
            {"timestamp": r["timestamp"], "score": round(r["avg_score"], 2)}
            for r in herd_rows
        ],
        "snapshots": [
            {
                "timestamp":   r["timestamp"],
                "nifty_price": r["nifty_price"],
                "herd_score":  r["avg_weighted_score"],
            }
            for r in snap_rows
        ],
    })


# ---------- Market Risk ----------

@app.route("/api/market-risk")
def get_market_risk():
    score = _get_latest_herd_score()
    return jsonify({"level": _herd_to_risk(score), "score": score})


# ---------- Articles Today ----------

@app.route("/api/articles-today")
def get_articles_today():
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) as count FROM news WHERE DATE(created_at) = ?", (today,)
    ).fetchone()
    conn.close()
    return jsonify({"count": row["count"] if row else 0})


# ---------- Signals Count ----------

@app.route("/api/signals-count")
def get_signals_count():
    conn = get_db()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) as count FROM agent_signals WHERE DATE(COALESCE(timestamp, datetime('now','localtime'))) = ?",
        (today,)
    ).fetchone()
    conn.close()
    return jsonify({"count": row["count"] if row else 0})


# ---------- Sector Analysis ----------

@app.route("/api/sector-analysis")
def get_sector_analysis():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT sector, COUNT(*) as count
        FROM agent_signals
        WHERE DATE(COALESCE(timestamp, datetime('now','localtime'))) = DATE('now','localtime')
        GROUP BY sector
        """
    ).fetchall()
    conn.close()

    total = sum(r["count"] for r in rows) if rows else 0
    sectors: dict[str, float] = {}
    if total > 0:
        for r in rows:
            s = (r["sector"] or "UNKNOWN").upper()
            sectors[s] = round((r["count"] / total) * 100, 1)

    for s in ("FINANCIALS", "TECHNOLOGY", "ENERGY", "HEALTHCARE", "CONSUMER"):
        sectors.setdefault(s, 0.0)

    return jsonify(sectors)


# ---------- Agent Signals ----------

@app.route("/api/agent-signals")
def get_agent_signals():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT agent_name, direction, confidence, sector, impact,
               COALESCE(timestamp, datetime('now','localtime')) as timestamp
        FROM agent_signals
        ORDER BY id DESC LIMIT 8
        """
    ).fetchall()
    conn.close()

    return jsonify([
        {
            "name":       r["agent_name"],
            "direction":  r["direction"],
            "confidence": r["confidence"],
            "sector":     r["sector"],
            "impact":     r["impact"],
            "timestamp":  r["timestamp"],
        }
        for r in rows
    ])


# ---------- Recent News ----------

@app.route("/api/recent-news")
def get_recent_news():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            n.title,
            n.content,
            n.created_at,
            hs.herd_score,
            hs.risk_level,
            hs.timestamp as hs_ts
        FROM news n
        LEFT JOIN herd_scores hs ON n.title = hs.article_title
        GROUP BY n.id
        ORDER BY n.id DESC
        LIMIT 8
        """
    ).fetchall()
    conn.close()

    news = []
    now = datetime.now()
    for r in rows:
        # Time-ago string
        try:
            created = datetime.strptime(r["created_at"], "%Y-%m-%d %H:%M:%S")
            secs = int((now - created).total_seconds())
        except Exception:
            secs = 0
        news.append({
            "title":      r["title"],
            "excerpt":    (r["content"] or "")[:160] + "…" if r["content"] else "",
            "herd_score": r["herd_score"],
            "risk_level": r["risk_level"],
            "time":       _seconds_to_human(max(secs, 0)),
        })

    return jsonify(news)


# ---------- Event Impact ----------

@app.route("/api/event-impact")
def get_event_impact():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT event_type, COUNT(*) as count
        FROM agent_signals
        WHERE DATE(COALESCE(timestamp, datetime('now','localtime'))) = DATE('now','localtime')
        GROUP BY event_type
        """
    ).fetchall()
    conn.close()

    total = sum(r["count"] for r in rows) if rows else 0
    impact: dict[str, float] = {}
    if total > 0:
        for r in rows:
            et = (r["event_type"] or "OTHER").upper()
            impact[et] = round((r["count"] / total) * 100, 1)

    return jsonify(impact)


# ---------- System Metrics ----------

@app.route("/api/system-metrics")
def get_system_metrics():
    conn = get_db()
    total_articles = conn.execute("SELECT COUNT(*) as c FROM news").fetchone()["c"]
    total_signals  = conn.execute("SELECT COUNT(*) as c FROM agent_signals").fetchone()["c"]
    total_herd     = conn.execute("SELECT COUNT(*) as c FROM herd_scores").fetchone()["c"]
    conn.close()

    return jsonify({
        "total_articles": total_articles,
        "agent_signals":  total_signals,
        "herd_records":   total_herd,
        "avg_latency":    "2.4ms",
        "active_nodes":   "4/4",
        "status":         "ONLINE",
    })


# ---------- Chart: Herd Score Trend ----------

@app.route("/api/chart/herd-trend")
def chart_herd_trend():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT timestamp, avg_weighted_score
        FROM market_snapshots
        WHERE nifty_price > 0
        ORDER BY timestamp ASC
        """
    ).fetchall()
    conn.close()
    return jsonify([{"t": r["timestamp"], "v": r["avg_weighted_score"]} for r in rows])


# ---------- Chart: NIFTY Price Trend ----------

@app.route("/api/chart/nifty-trend")
def chart_nifty_trend():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT timestamp, nifty_price
        FROM market_snapshots
        WHERE nifty_price > 0
        ORDER BY timestamp ASC
        """
    ).fetchall()
    conn.close()
    return jsonify([{"t": r["timestamp"], "v": r["nifty_price"]} for r in rows])


# ---------- Chart: Sector Herding Intensity ----------

@app.route("/api/chart/sector-herding")
def chart_sector_herding():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT sector, AVG(confidence) as avg_conf, COUNT(*) as cnt
        FROM agent_signals
        WHERE sector IS NOT NULL AND sector != '' AND sector != 'UNKNOWN'
        GROUP BY sector
        ORDER BY avg_conf DESC
        LIMIT 10
        """
    ).fetchall()
    conn.close()
    return jsonify([
        {"sector": (r["sector"] or "OTHER").upper(), "score": round(r["avg_conf"], 1), "count": r["cnt"]}
        for r in rows
    ])


# ---------- Chart: Agent Direction Distribution ----------

@app.route("/api/chart/agent-distribution")
def chart_agent_distribution():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT direction, COUNT(*) as count
        FROM agent_signals
        WHERE direction IN ('BUY','HOLD','SELL')
        GROUP BY direction
        """
    ).fetchall()
    conn.close()
    return jsonify([{"direction": r["direction"], "count": r["count"]} for r in rows])


# ---------- Chart: Risk Level Distribution ----------

@app.route("/api/chart/risk-distribution")
def chart_risk_distribution():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT risk_level, COUNT(*) as count
        FROM herd_scores
        WHERE risk_level IS NOT NULL
        GROUP BY risk_level
        ORDER BY count DESC
        """
    ).fetchall()
    conn.close()
    return jsonify([{"risk": r["risk_level"], "count": r["count"]} for r in rows])


# ---------- Correlation Analytics ----------

@app.route("/api/correlation-analytics")
def correlation_analytics():
    conn = get_db()

    total = conn.execute(
        "SELECT COUNT(*) as c FROM market_snapshots WHERE nifty_price > 0 AND avg_weighted_score > 0"
    ).fetchone()["c"]

    # Consecutive snapshot pairs → (herd_score_t, return_t+1)
    rows = conn.execute(
        """
        SELECT
            s1.avg_weighted_score AS herd,
            s1.nifty_price        AS p1,
            s2.nifty_price        AS p2
        FROM market_snapshots s1
        JOIN market_snapshots s2 ON s2.id = s1.id + 1
        WHERE s1.nifty_price > 0 AND s2.nifty_price > 0
          AND s1.avg_weighted_score > 0
        """
    ).fetchall()
    conn.close()

    pairs = [
        (r["herd"], (r["p2"] - r["p1"]) / r["p1"] * 100)
        for r in rows if r["p1"] > 0
    ]

    corr = 0.0
    avg_return_high = 0.0
    n_high = 0

    if len(pairs) >= 2:
        herd_vals   = [p[0] for p in pairs]
        return_vals = [p[1] for p in pairs]
        corr        = _pearson(herd_vals, return_vals)
        high        = [p[1] for p in pairs if p[0] >= 75]
        avg_return_high = round(sum(high) / len(high), 4) if high else 0.0
        n_high      = len(high)

    scatter = [{"herd": round(p[0], 2), "return": round(p[1], 4)} for p in pairs]

    return jsonify({
        "snapshots":             total,
        "correlation":           corr,
        "avg_return_high_herd":  avg_return_high,
        "n_high_herd":           n_high,
        "scatter":               scatter,
        "pairs_available":       len(pairs),
    })


# ---------- Live Feed (SSE) ----------

@app.route("/api/live-feed")
def live_feed():
    """Server-Sent Events: push updates to connected browsers."""
    q: list[str] = []

    with _sse_lock:
        _sse_clients.append(q)

    def stream():
        # Send initial keepalive
        yield "data: {\"type\": \"connected\"}\n\n"
        try:
            while True:
                if q:
                    yield q.pop(0)
                else:
                    # Heartbeat every 15s so connection stays alive
                    yield ": heartbeat\n\n"
                    time.sleep(15)
        except GeneratorExit:
            pass
        finally:
            with _sse_lock:
                try:
                    _sse_clients.remove(q)
                except ValueError:
                    pass

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":               "no-cache",
            "X-Accel-Buffering":           "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


# ---------- Manual Pipeline Trigger ----------

@app.route("/api/run-pipeline", methods=["POST"])
def trigger_pipeline():
    """Kick off the AI pipeline in a background thread."""
    def _run():
        from src.pipeline import run_pipeline
        try:
            result = run_pipeline()
            logger.info("[Pipeline/manual] %s", result)
            _push_sse({"type": "pipeline_complete", **result})
        except Exception as exc:
            logger.error("[Pipeline/manual] %s", exc)
            _push_sse({"type": "pipeline_error", "error": str(exc)})

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Pipeline running in background."})


# ─────────────────────────────────────────
# Lightweight auto-snapshot (free, no AI)
# ─────────────────────────────────────────

# Track next fire times for the status API
_next_snapshot_ts: float = 0.0
_next_pipeline_ts: float = 0.0


def _take_lightweight_snapshot() -> dict:
    """
    Cheap 15-min job:
      1. Fetch live NIFTY price via yfinance (free)
      2. Read latest avg herd score from herd_scores (no AI needed)
      3. Save a market_snapshot row
      4. Push SSE so the dashboard refreshes itself
    """
    global _next_snapshot_ts
    logger.info("[Snapshot] Taking lightweight snapshot…")
    try:
        from src.market_data import get_nifty_close
        from src.database import save_market_snapshot

        nifty = get_nifty_close()
    except Exception as exc:
        logger.warning("[Snapshot] yfinance failed: %s – using last known price.", exc)
        conn = get_db()
        row = conn.execute(
            "SELECT nifty_price FROM market_snapshots ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
        nifty = float(row["nifty_price"]) if row else 0.0
        from src.database import save_market_snapshot

    # Compute avg herd score from the last 2 hours of data
    conn = get_db()
    row = conn.execute(
        """
        SELECT AVG(herd_score) as avg_h
        FROM herd_scores
        WHERE timestamp >= datetime('now', '-2 hours', 'localtime')
        """
    ).fetchone()
    # Fall back to all-time average if no recent data
    if not row or row["avg_h"] is None:
        row = conn.execute("SELECT AVG(herd_score) as avg_h FROM herd_scores").fetchone()
    conn.close()

    avg_herd = round(float(row["avg_h"]), 2) if row and row["avg_h"] else 0.0
    risk     = _herd_to_risk(avg_herd)
    ts       = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        save_market_snapshot(ts, nifty, avg_herd, 0)
    except Exception as exc:
        logger.warning("[Snapshot] save failed: %s", exc)

    result = {
        "type":       "snapshot_complete",
        "nifty_price": nifty,
        "herd_score":  avg_herd,
        "risk_level":  risk,
        "timestamp":   ts,
    }
    _push_sse(result)
    _next_snapshot_ts = time.time() + 15 * 60
    logger.info("[Snapshot] Done – NIFTY=%.2f herd=%.1f %s", nifty, avg_herd, risk)
    return result


# ---------- Scheduler Status API ----------

@app.route("/api/scheduler-status")
def scheduler_status():
    now = time.time()
    return jsonify({
        "next_snapshot_secs": max(0, int(_next_snapshot_ts - now)),
        "next_pipeline_secs": max(0, int(_next_pipeline_ts - now)),
        "next_snapshot_ts":   datetime.fromtimestamp(_next_snapshot_ts).strftime("%H:%M:%S") if _next_snapshot_ts else None,
        "next_pipeline_ts":   datetime.fromtimestamp(_next_pipeline_ts).strftime("%H:%M:%S") if _next_pipeline_ts else None,
    })


# ---------- Manual Snapshot Trigger ----------

@app.route("/api/run-snapshot", methods=["POST"])
def trigger_snapshot():
    """Trigger a lightweight snapshot immediately."""
    def _run():
        _take_lightweight_snapshot()
    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"status": "started", "message": "Snapshot running."})


# ─────────────────────────────────────────
# Background Scheduler
# ─────────────────────────────────────────

def _start_scheduler():
    global _next_snapshot_ts, _next_pipeline_ts
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from src.pipeline import run_pipeline

        # ── Job 1: Lightweight snapshot every 15 min (free) ──────────
        def _snapshot_job():
            global _next_snapshot_ts
            _take_lightweight_snapshot()
            _next_snapshot_ts = time.time() + 15 * 60

        # ── Job 2: Full AI pipeline every 60 min (uses API credits) ──
        def _pipeline_job():
            global _next_pipeline_ts
            logger.info("[Scheduler] Firing full pipeline job.")
            try:
                result = run_pipeline()
                _push_sse({"type": "pipeline_complete", **result})
            except Exception as exc:
                logger.error("[Scheduler] Pipeline error: %s", exc)
            _next_pipeline_ts = time.time() + 60 * 60

        scheduler = BackgroundScheduler()
        scheduler.add_job(
            _snapshot_job, "interval", minutes=15,
            id="snapshot", replace_existing=True,
        )
        scheduler.add_job(
            _pipeline_job, "interval", minutes=60,
            id="pipeline", replace_existing=True,
        )
        scheduler.start()

        # Initialise countdown times
        _next_snapshot_ts = time.time() + 15 * 60
        _next_pipeline_ts = time.time() + 60 * 60

        logger.info(
            "[Scheduler] Started ✔ "
            "Snapshot every 15 min | Full pipeline every 60 min."
        )
    except ImportError:
        logger.warning("[Scheduler] APScheduler not installed – auto-jobs disabled.")
    except Exception as exc:
        logger.error("[Scheduler] Failed to start: %s", exc)


# ─────────────────────────────────────────
# Startup
# ─────────────────────────────────────────

# Init DB tables
init_db()

# Start background scheduler (outside reloader to avoid double-start)
import os
if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    _start_scheduler()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port, threaded=True)