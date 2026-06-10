<div align="center">

# 🧠 ConsensusIQ
### AI Herding & Market Stability Monitor

[![Python](https://img.shields.io/badge/Python-3.13+-blue?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![Groq](https://img.shields.io/badge/Powered_by-Groq_LLM-orange)](https://console.groq.com)
[![Tavily](https://img.shields.io/badge/News-Tavily_Search-green)](https://tavily.com)

**Real-time AI herding detection and market stability monitor for Indian equity markets powered by a multi-agent LLM pipeline.**

</div>

---

## 📌 What is ConsensusIQ?

ConsensusIQ tracks **AI herding** — the phenomenon where multiple AI agents make identical market decisions, which can amplify volatility just like human herd behaviour.

The platform:
- Fetches live Indian market news every 15 minutes via **Tavily Search**
- Runs 4 independent AI agents (conservative, momentum, value, risk-averse) via **Groq LLaMA**
- Computes a **Herd Score** (0–100%) measuring consensus strength
- Stores all data in **SQLite** and visualises it on a real-time dashboard
- Calculates **Pearson correlation** between herd scores and future NIFTY returns — turning raw signals into validated research

---

## 🖥️ Dashboard Preview

| Section | What it shows |
|---------|--------------|
| **Hero Cards** | Live NIFTY 50 price · Herd Score · Articles ingested · AI signals |
| **Consensus Meter** | Animated SVG ring showing herd % with BUY/HOLD/SELL split |
| **Sparklines** | 24-hour herd score trend & NIFTY price trend |
| **Agent Signals Feed** | Last 8 agent decisions with direction, confidence, sector |
| **News Feed** | Last 8 articles with per-article herd scores |
| **Research Validation** | Herd Trend · NIFTY Trend · Sector Herding · Agent Distribution · Correlation Scatter |

---

## ⚙️ Architecture

```
Browser (SSE persistent connection)
    │
    ▼
Flask app.py ──────────────────────────────────────────────────
    │  14 REST API routes
    │  APScheduler:
    │    ├── Snapshot job  (every 15 min — free, yfinance)
    │    └── Pipeline job  (every 60 min — Tavily + Groq)
    ▼
src/pipeline.py ───────────────────────────────────────────────
    │  Tavily → fetch_market_news() (5 queries, 25 raw articles)
    │  Filter (bad keywords, min 200 chars, dedup)
    │  For each article (up to 10):
    │    ├─ 4 Groq agents: conservative, momentum, value, risk_averse
    │    ├─ save_agent_signal() × 4
    │    └─ calculate_weighted_consensus() → save_herd_score()
    │  yfinance → get_nifty_close() → save_market_snapshot()
    └─ Push SSE event to all connected browsers
    ▼
SQLite  market_news.db ─────────────────────────────────────────
    tables: news · signals · agent_signals
            herd_scores · market_snapshots · correlation_results
```

---

## 🚀 Quick Start

### 1. Clone & install

```bash
git clone https://github.com/your-username/AI-HERDING.git
cd AI-HERDING

# Install uv (fast Python package manager)
pip install uv

# Create venv & install all dependencies
uv sync
```

### 2. Configure API keys

```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY and TAVILY_API_KEY
```

### 3. Run the server

```bash
uv run python app.py
```

Open **http://127.0.0.1:5000** in your browser. 🎉

---

## 🔑 API Keys Required

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| [Groq](https://console.groq.com) | LLaMA 3.3-70B agent inference | ✅ Yes |
| [Tavily](https://tavily.com) | Market news search | ✅ Yes (1000 req/mo) |
| yfinance | NIFTY 50 price data | ✅ Free, no key needed |

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/nifty-price` | Latest NIFTY 50 price |
| `GET` | `/api/herd-score` | Latest herd score + risk level |
| `GET` | `/api/herd-history` | 24h rolling herd + NIFTY data |
| `GET` | `/api/agent-signals` | Last 8 AI agent signals |
| `GET` | `/api/recent-news` | Last 8 articles with herd scores |
| `GET` | `/api/sector-analysis` | Sector % breakdown |
| `GET` | `/api/chart/herd-trend` | All-time herd score series |
| `GET` | `/api/chart/nifty-trend` | All-time NIFTY price series |
| `GET` | `/api/chart/sector-herding` | Sector avg confidence |
| `GET` | `/api/chart/agent-distribution` | BUY/HOLD/SELL counts |
| `GET` | `/api/correlation-analytics` | Pearson r + scatter data |
| `GET` | `/api/scheduler-status` | Next snapshot/pipeline times |
| `GET` | `/api/live-feed` | **SSE** — real-time push updates |
| `POST` | `/api/run-pipeline` | Manually trigger full pipeline |
| `POST` | `/api/run-snapshot` | Manually trigger NIFTY snapshot |

---

## 📁 Project Structure

```
AI-HERDING/
├── app.py                  # Flask server — all API routes + scheduler
├── pyproject.toml          # Python project config & dependencies
├── uv.lock                 # Pinned dependency lockfile
├── .env.example            # Environment variable template
│
├── src/                    # Core business logic
│   ├── pipeline.py         # End-to-end orchestration
│   ├── database.py         # SQLite thread-safe operations
│   ├── groq_agent.py       # LLM agent runner
│   ├── agents.py           # Agent persona definitions
│   ├── herd_score.py       # Weighted consensus calculator
│   ├── news_collector.py   # Tavily news fetcher
│   ├── market_data.py      # yfinance NIFTY fetcher
│   └── __init__.py
│
├── templates/
│   └── dashboard.html      # Full dark-mode dashboard (Chart.js + SSE)
│
├── data/                   # Runtime data (gitignored)
│   └── logs/
│
├── main.py                 # CLI entry point
├── test_agents.py          # Agent unit tests
├── test_market.py          # Market data tests
├── build_dataset.py        # Dataset builder utility
├── check_herd.py           # Quick herd score checker
├── check_sector.py         # Sector analysis utility
└── correlation_engine.py   # Standalone correlation calculator
```

---

## 🧪 Agents

| Agent | Strategy | Bias |
|-------|---------|------|
| **Conservative** | Avoids volatility, prefers stable sectors | HOLD/SELL |
| **Momentum** | Follows trends, buys strength | BUY |
| **Value** | Fundamentals-focused | Contrarian |
| **Risk-Averse** | Capital preservation first | HOLD/SELL |

---

## 📊 Herd Score Interpretation

| Score | Risk Level | Meaning |
|-------|-----------|---------|
| 0–54% | 🟢 LOW | Agents disagree — healthy market |
| 55–69% | 🟡 MEDIUM | Moderate consensus forming |
| 70–84% | 🟠 HIGH | Strong herding — watch for reversals |
| 85–100% | 🔴 CRITICAL | Extreme herding — systemic risk signal |

---

## 🤝 Contributing

Pull requests are welcome! Please open an issue first to discuss major changes.

---

## 📄 License

MIT © 2026
