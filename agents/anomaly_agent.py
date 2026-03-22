import numpy as np
from scipy import stats
from agents.sentiment_agent import AgentState
 
 
Z_THRESHOLD = 2.0   # flag anything beyond 2 standard deviations
 
 
def detect_anomalies(sentiment_scores: list[dict]) -> list[dict]:
    if len(sentiment_scores) < 5:
        return []
 
    scores = [s["score"] for s in sentiment_scores]
    mean   = float(np.mean(scores))
    std    = float(np.std(scores))
 
    anomalies = []
    for i, item in enumerate(sentiment_scores):
        z = (item["score"] - mean) / std if std > 0 else 0.0
        if abs(z) >= Z_THRESHOLD:
            anomalies.append({
                "index":     i,
                "text":      item["text"][:120],
                "score":     item["score"],
                "label":     item["label"],
                "z_score":   round(z, 3),
                "direction": "spike" if z > 0 else "drop",
                "severity":  "high" if abs(z) >= 3.0 else "medium",
            })
 
    return anomalies
 
 
def anomaly_agent(state: AgentState) -> AgentState:
    scores = state.get("sentiment_scores", [])
    anomalies = detect_anomalies(scores)
 
    print(f"[AnomalyAgent] Checked {len(scores)} items → "
          f"{len(anomalies)} anomalies found")
    for a in anomalies:
        print(f"  {a['direction'].upper():5s} z={a['z_score']:+.2f} | {a['text'][:60]}")
 
    return {**state, "anomalies": anomalies}
 
 
if __name__ == "__main__":
    dummy_scores = [
        {"text": f"Headline {i}", "score": float(np.random.normal(0.2, 0.3))}
        for i in range(30)
    ]
    dummy_scores[5]["score"]  =  0.95   # artificial spike
    dummy_scores[15]["score"] = -0.90   # artificial drop
 
    result = detect_anomalies(dummy_scores)
    for r in result:
        print(r)