# IndustryIQ

IndustryIQ is a multi-agent AI dashboard for tracking brand sentiment, short-term forecasting, anomaly detection, competitor positioning, and executive insights across industries like hotels, airlines, and finance.

## Architecture

```text
Frontend (Next.js 16 + Tailwind + Recharts)
        |
        v
Backend API (FastAPI)
        |
        v
LangGraph Pipeline
  1. Sentiment Agent   -> FinBERT scores live NewsAPI headlines
  2. Forecasting Agent -> Prophet projects 30/60/90 day outlook
  3. Anomaly Agent     -> z-score detection on sentiment outliers
  4. Competitor Agent  -> ChromaDB-based peer sentiment ranking
  5. Insight Agent     -> GPT-generated executive brief
        |
        +--> SQLite run history
        +--> PDF export
        +--> ChromaDB sentiment store
```

## Local Setup

1. Clone the repo.
2. Create and activate a Python virtual environment.
3. Install backend dependencies:

```powershell
pip install -r requirements.txt
```

4. Install frontend dependencies:

```powershell
cd frontend
npm install
```

5. Create a root `.env` file:

```env
OPENAI_API_KEY=your_openai_key
NEWSAPI_KEY=your_newsapi_key
CHROMA_PATH=./chroma_db
DB_PATH=./db/history.db
PORT=8000
```

6. Start the backend:

```powershell
cd c:\Users\shaha\industry-iq
venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

7. Start the frontend:

```powershell
cd c:\Users\shaha\industry-iq\frontend
npm run dev
```

8. Open `http://localhost:3000`.

## Environment Variables

- `OPENAI_API_KEY`: OpenAI key for executive brief generation
- `NEWSAPI_KEY`: NewsAPI key for live headline fetching
- `CHROMA_PATH`: ChromaDB storage path
- `DB_PATH`: SQLite database path
- `PORT`: backend port for local/dev/prod runtime
- `NEXT_PUBLIC_API_URL`: frontend API base URL, usually set in `frontend/.env.local`

## Deployment

### Railway Backend

- Uses `Procfile`
- Uses `railway.json`
- Set these Railway variables:
  - `OPENAI_API_KEY`
  - `NEWSAPI_KEY`
  - `CHROMA_PATH`
  - `DB_PATH`
  - `PORT`

### Vercel Frontend

- Set `NEXT_PUBLIC_API_URL` to your Railway backend URL
- `frontend/vercel.json` is included

## Tech Stack

- FastAPI
- LangGraph
- LangChain
- OpenAI
- FinBERT via Transformers
- Prophet
- ChromaDB
- SQLite
- ReportLab
- Next.js 16
- Tailwind CSS
- Recharts
