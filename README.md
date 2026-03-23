# IndustryIQ - Multi-Agent AI Intelligence Dashboard

> **Live App**: https://industry-iq.vercel.app  
> **Backend API**: https://web-production-47a64.up.railway.app/health

A production-grade multi-agent AI system that analyzes brand sentiment,
forecasts demand, detects anomalies, and generates executive intelligence
reports across hotels, airlines, and finance industries.

---

## Live Demo

Select any industry and brand, click **Run agents**, and watch 5 AI
agents collaborate to produce a complete intelligence briefing in real time.

---

## How It Works - 5-Agent Pipeline

```text
User Query
|
v
+---------------------------------------------+
|           LangGraph Orchestrator            |
|                                             |
|  +-------------+    +---------------------+ |
|  |  Sentiment  |--->|   Forecasting Agent | |
|  |   Agent     |    |  (Prophet 30/60/90d)| |
|  |  (VADER NLP)|    +---------------------+ |
|  +-------------+    +---------------------+ |
|         |           |   Anomaly Agent     | |
|         +---------->|   (Z-score detect)  | |
|         |           +---------------------+ |
|         |           +---------------------+ |
|         +---------->|  Competitor Agent   | |
|                     |  (ChromaDB RAG)     | |
|                     +---------------------+ |
|                              |              |
|                              v              |
|                     +---------------------+ |
|                     |   Insight Agent     | |
|                     |   (GPT-4o-mini)     | |
|                     +---------------------+ |
+---------------------------------------------+
|
v
Dashboard (Next.js + Recharts + Dark Mode)
SQLite Run History + PDF Export + ChromaDB
```

---

## Features

| Feature | Description |
|---|---|
| 5-Agent Pipeline | LangGraph orchestrates sentiment, forecast, anomaly, competitor, and insight agents |
| Live News Feed | NewsAPI fetches real headlines per brand |
| Demand Forecasting | Facebook Prophet projects 30/60/90-day outlook |
| Anomaly Detection | Z-score flags unusual sentiment spikes or drops |
| Competitor Ranking | ChromaDB-powered peer sentiment comparison |
| GPT-4 Insights | Executive brief generated per run |
| Dark Mode | Full dark/light theme toggle |
| Run History | SQLite stores every run with timeline chart |
| PDF + CSV Export | Download full intelligence report |
| Global Timezone | Timestamps auto-convert to user local time |

---

## Tech Stack

**Backend**
- Python, FastAPI, LangGraph, LangChain
- VADER Sentiment, Facebook Prophet
- ChromaDB, SQLite, ReportLab
- OpenAI GPT-4o-mini, NewsAPI

**Frontend**
- Next.js 16, TypeScript, Tailwind CSS
- Recharts, Dark mode

**Deployment**
- Railway (backend), Vercel (frontend)

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key
- NewsAPI key (free at newsapi.org)

### 1. Clone and install backend
```bash
git clone https://github.com/shanmathy-ravisankaran/industry-iq.git
cd industry-iq
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Install frontend
```bash
cd frontend
npm install
```

### 3. Create .env file
Create a `.env` file in the root directory with your API keys.
See **Environment Variables** section below for what keys are needed.

### 4. Create frontend/.env.local
Create `frontend/.env.local` and set the backend URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Environment Variables

| Variable | Where to get it | Required |
|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com | Yes |
| `NEWSAPI_KEY` | newsapi.org (free) | Yes |
| `CHROMA_PATH` | Set to `./chroma_db` | Yes |
| `DB_PATH` | Set to `./db/history.db` | Yes |
| `PORT` | Set to `8000` | Yes |
| `NEXT_PUBLIC_API_URL` | Your Railway URL in production | Yes |

> Never commit your `.env` file to GitHub.  
> It is already added to `.gitignore`.

```text
industry-iq/
├── agents/
│   ├── sentiment_agent.py    # VADER sentiment scoring
│   ├── forecasting_agent.py  # Prophet time-series
│   ├── anomaly_agent.py      # Z-score detection
│   ├── competitor_agent.py   # ChromaDB peer ranking
│   ├── insight_agent.py      # GPT-4 executive brief
│   ├── news_fetcher.py       # NewsAPI integration
│   └── graph.py              # LangGraph pipeline
├── db/
│   └── database.py           # SQLite run history
├── frontend/
│   └── app/
│       └── page.tsx          # Main dashboard
├── main.py                   # FastAPI backend
├── requirements.txt
└── README.md
```

---

## Supported Industries & Brands

| Industry | Brands |
|---|---|
| Hotels | Marriott, Hilton, IHG, Hyatt, Wyndham |
| Airlines | Delta, United, American, Southwest, JetBlue |
| Finance | JPMorgan, Goldman, Morgan Stanley, Citi, BofA |
