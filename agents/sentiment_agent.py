import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from typing import TypedDict
import chromadb
import uuid
import os

chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMA_PATH", "./chroma_db"))
collection = chroma_client.get_or_create_collection("sentiment_store")
analyzer = SentimentIntensityAnalyzer()

class AgentState(TypedDict):
    industry: str
    brand: str
    headlines: list[str]
    sentiment_scores: list[dict]
    forecast: list[dict]
    anomalies: list[dict]
    competitor_delta: list[dict]
    insight_report: str

def score_headline(text: str) -> dict:
    scores = analyzer.polarity_scores(text)
    sentiment_score = round(scores["compound"], 4)
    if sentiment_score > 0.2:
        label = "bullish"
    elif sentiment_score < -0.2:
        label = "bearish"
    else:
        label = "neutral"
    confidence = round(max(scores["pos"], scores["neg"], scores["neu"]) * 100, 1)
    return {
        "text": text,
        "score": sentiment_score,
        "label": label,
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "confidence_pct": confidence,
    }

def load_financial_news_sample(n: int = 50) -> list[str]:
    csv_path = os.path.join("data", "sentiment", "all-data.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding="latin-1", header=None, names=["label", "text"])
        return df["text"].dropna().head(n).tolist()
    return []

def store_in_chroma(scored: list[dict], brand: str, industry: str):
    for item in scored:
        collection.add(
            documents=[item["text"]],
            metadatas=[{"score": item["score"], "label": item["label"], "brand": brand, "industry": industry}],
            ids=[str(uuid.uuid4())],
        )

def sentiment_agent(state: AgentState) -> AgentState:
    brand = state.get("brand", "General")
    industry = state.get("industry", "Finance")
    
    headlines = state.get("headlines") or []
    
    if not headlines:
        try:
            from agents.news_fetcher import fetch_headlines
            headlines = fetch_headlines(brand, industry, page_size=50)
            print(f"[SentimentAgent] Got {len(headlines)} live headlines")
        except Exception as e:
            print(f"[SentimentAgent] NewsAPI failed: {e}")
            headlines = []
    
    if not headlines:
        headlines = load_financial_news_sample(50)
    
    if not headlines:
        import random
        random.seed(hash(brand) % 9999)
        base_headlines = [
            f"{brand} reports strong quarterly revenue growth beating expectations",
            f"{brand} faces regulatory scrutiny amid market competition concerns",
            f"{brand} announces strategic expansion into new markets globally",
            f"{brand} customer satisfaction scores reach record high levels",
            f"{brand} stock performance shows resilience despite market volatility",
            f"{brand} launches innovative service improving operational efficiency",
            f"{brand} management team announces ambitious five year growth plan",
            f"{brand} faces cost pressure as supply chain disruptions continue",
            f"{brand} partnership deal expected to drive significant revenue increase",
            f"{brand} investor confidence grows following positive earnings report",
        ]
        headlines = base_headlines

    scored = [score_headline(h) for h in headlines]
    store_in_chroma(scored, brand, industry)
    avg_score = round(sum(s["score"] for s in scored) / len(scored), 4)
    print(f"[SentimentAgent] {len(scored)} headlines | avg={avg_score}")
    return {**state, "sentiment_scores": scored}
