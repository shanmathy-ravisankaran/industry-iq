import os
import uuid
from typing import TypedDict

import chromadb
from transformers import pipeline

from agents.news_fetcher import fetch_headlines, fetch_live_headlines

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection("sentiment_store")

print("Loading FinBERT model...")
finbert = pipeline(
    "text-classification",
    model="ProsusAI/finbert",
    top_k=None,
)
print("FinBERT ready.")


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
    raw_results = finbert(text[:512])

    if raw_results and isinstance(raw_results, list) and isinstance(raw_results[0], list):
        results = raw_results[0]
    else:
        results = raw_results

    scores = {r["label"]: r["score"] for r in results}
    sentiment_score = scores.get("positive", 0) - scores.get("negative", 0)

    if sentiment_score > 0.2:
        label = "bullish"
    elif sentiment_score < -0.2:
        label = "bearish"
    else:
        label = "neutral"

    return {
        "text": text,
        "score": round(sentiment_score, 4),
        "label": label,
        "positive": round(scores.get("positive", 0), 4),
        "negative": round(scores.get("negative", 0), 4),
        "neutral": round(scores.get("neutral", 0), 4),
        "confidence": round(
            max(
                scores.get("positive", 0),
                scores.get("negative", 0),
                scores.get("neutral", 0),
            )
            * 100,
            2,
        ),
    }
def store_in_chroma(scored: list[dict], brand: str, industry: str):
    try:
        for item in scored:
            collection.add(
                documents=[item["text"]],
                metadatas=[{
                    "score": item["score"],
                    "label": item["label"],
                    "brand": brand,
                    "industry": industry,
                    "confidence": item["confidence"],
                }],
                ids=[str(uuid.uuid4())],
            )
    except Exception as e:
        print(f"[SentimentAgent] Chroma storage skipped: {e}")


def sentiment_agent(state: AgentState) -> AgentState:
    brand = state.get("brand", "General")
    industry = state.get("industry", "Finance")
    provided_headlines = state.get("headlines") or []
    if provided_headlines:
        headlines = provided_headlines
        print(f"[SentimentAgent] Using {len(headlines)} provided headlines.")
    else:
        live_headlines = fetch_live_headlines(brand=brand, industry=industry, page_size=50)
        if len(live_headlines) >= 5:
            headlines = live_headlines
            print(f"[SentimentAgent] Using {len(headlines)} live NewsAPI headlines.")
        else:
            headlines = fetch_headlines(brand=brand, industry=industry, page_size=50)
            print(f"[SentimentAgent] Using {len(headlines)} fallback CSV headlines.")

    scored = [score_headline(h) for h in headlines]
    store_in_chroma(scored, brand, industry)

    avg_score = round(sum(s["score"] for s in scored) / len(scored), 4) if scored else 0.0
    print(f"[SentimentAgent] {len(scored)} headlines | avg score: {avg_score}")

    return {**state, "sentiment_scores": scored}


if __name__ == "__main__":
    test_headlines = fetch_headlines("Marriott", "Hotels", page_size=10)
    for h in test_headlines:
        result = score_headline(h)
        print(f"{result['label']:8s} {result['score']:+.3f} {result['confidence']:6.2f}% {h[:80]}")
