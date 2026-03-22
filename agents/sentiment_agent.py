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
    df = pd.read_csv(csv_path, encoding="latin-1", header=None, names=["label", "text"])
    return df["text"].dropna().head(n).tolist()

def store_in_chroma(scored: list[dict], brand: str, industry: str):
    for item in scored:
        collection.add(
            documents=[item["text"]],
            metadatas=[{"score": item["score"], "label": item["label"], "brand": brand, "industry": industry}],
            ids=[str(uuid.uuid4())],
        )

def sentiment_agent(state: AgentState) -> AgentState:
    headlines = state.get("headlines") or load_financial_news_sample(50)
    brand = state.get("brand", "General")
    industry = state.get("industry", "Finance")
    scored = [score_headline(h) for h in headlines]
    store_in_chroma(scored, brand, industry)
    avg_score = round(sum(s["score"] for s in scored) / len(scored), 4)
    print(f"[SentimentAgent] {len(scored)} headlines | avg score: {avg_score}")
    return {**state, "sentiment_scores": scored}