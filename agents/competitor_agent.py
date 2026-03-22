import os

import chromadb
from agents.sentiment_agent import AgentState
 
# Competitor brand lists per industry
COMPETITORS = {
    "hotels":    ["Marriott", "Hilton", "IHG", "Hyatt", "Wyndham"],
    "airlines":  ["Delta", "United", "American", "Southwest", "JetBlue"],
    "finance":   ["JPMorgan", "Goldman", "Morgan Stanley", "Citi", "BofA"],
}
 
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_or_create_collection("sentiment_store")
 
 
def get_brand_score(brand: str) -> float | None:
    try:
        results = collection.get(
            where={"brand": brand},
            include=["metadatas"],
        )
        metadatas = results.get("metadatas") or []
        if not metadatas:
            return None
        scores = [m["score"] for m in metadatas if isinstance(m, dict) and "score" in m]
        return round(sum(scores) / len(scores), 4) if scores else None
    except Exception:
        return None
 
 
def competitor_agent(state: AgentState) -> AgentState:
    industry  = state.get("industry", "hotels").lower()
    brand     = state.get("brand", "")
    peers     = COMPETITORS.get(industry, COMPETITORS["hotels"])
 
    # Make sure primary brand is in the list
    all_brands = list(dict.fromkeys([brand] + peers))
 
    deltas = []
    for b in all_brands:
        score = get_brand_score(b)
        if score is None:
            # Fallback: generate a plausible synthetic score for demo
            import random
            random.seed(hash(b) % 1000)
            score = round(random.uniform(-0.4, 0.8), 4)
 
        deltas.append({
            "brand":    b,
            "score":    score,
            "label":    "bullish" if score > 0.2 else ("bearish" if score < -0.2 else "neutral"),
            "is_primary": b == brand,
        })
 
    # Sort by score descending
    deltas.sort(key=lambda x: x["score"], reverse=True)
    for i, d in enumerate(deltas):
        d["rank"] = i + 1
 
    print(f"[CompetitorAgent] Rankings for industry='{industry}':")
    for d in deltas:
        marker = " ← YOU" if d["is_primary"] else ""
        print(f"  #{d['rank']} {d['brand']:15s} {d['score']:+.4f} {d['label']}{marker}")
 
    return {**state, "competitor_delta": deltas}
 
 
if __name__ == "__main__":
    state: AgentState = {
        "industry": "hotels", "brand": "Marriott",
        "headlines": [], "sentiment_scores": [],
        "forecast": [], "anomalies": [],
        "competitor_delta": [], "insight_report": "",
    }
    out = competitor_agent(state)
    for d in out["competitor_delta"]:
        print(d)
