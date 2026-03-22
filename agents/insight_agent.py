import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from agents.sentiment_agent import AgentState
from dotenv import load_dotenv
 
load_dotenv()
 
llm = ChatOpenAI(
    model="gpt-4o-mini",          # cost-efficient, fast
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY"),
)
 
SYSTEM_PROMPT = """You are an expert industry analyst AI. You receive structured 
data from multiple analysis agents and produce a concise, actionable executive 
summary in plain English. Be specific with numbers. Keep it under 150 words."""
 
 
def build_context(state: AgentState) -> str:
    scores   = state.get("sentiment_scores", [])
    forecast = state.get("forecast", [])
    anomalies = state.get("anomalies", [])
    competitors = state.get("competitor_delta", [])
    brand    = state.get("brand", "Unknown")
    industry = state.get("industry", "Unknown")
 
    avg_score = (
        round(sum(s["score"] for s in scores) / len(scores), 3)
        if scores else 0
    )
    bullish = sum(1 for s in scores if s["label"] == "bullish")
    bearish = sum(1 for s in scores if s["label"] == "bearish")
 
    fc_30 = forecast[0]["day_30"].get("forecast", "N/A") if forecast else "N/A"
    fc_90 = forecast[0]["day_90"].get("forecast", "N/A") if forecast else "N/A"
 
    top_competitor = (
        [c for c in competitors if not c["is_primary"]][0]["brand"]
        if competitors else "N/A"
    )
 
    anomaly_summary = (
        f"{len(anomalies)} anomalies detected — "
        + ", ".join(f"{a['direction']} (z={a['z_score']})" for a in anomalies[:3])
        if anomalies else "No anomalies detected."
    )
 
    return f"""
Industry: {industry}
Brand: {brand}
 
SENTIMENT ANALYSIS:
- Headlines analyzed: {len(scores)}
- Average score: {avg_score} (range -1.0 bearish to +1.0 bullish)
- Bullish: {bullish} | Bearish: {bearish}
 
FORECAST:
- 30-day outlook: {fc_30}
- 90-day outlook: {fc_90}
 
ANOMALIES:
- {anomaly_summary}
 
COMPETITIVE POSITION:
- Top competitor by sentiment: {top_competitor}
- Full ranking: {[f"{c['brand']} ({c['score']:+.2f})" for c in competitors[:4]]}
 
Please provide an actionable executive summary with key risks and opportunities.
"""
 
 
def insight_agent(state: AgentState) -> AgentState:
    context = build_context(state)
    print("[InsightAgent] Calling GPT-4o-mini for executive summary...")
 
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]
 
    try:
        response = llm.invoke(messages)
        report = response.content.strip()
        print(f"[InsightAgent] Report generated ({len(report)} chars)")
    except Exception as e:
        print(f"[InsightAgent] LLM call failed: {e}")
        report = build_fallback_report(state)
        print(f"[InsightAgent] Fallback report generated ({len(report)} chars)")

    return {**state, "insight_report": report}


def build_fallback_report(state: AgentState) -> str:
    scores = state.get("sentiment_scores", [])
    forecast = state.get("forecast", [])
    anomalies = state.get("anomalies", [])
    competitors = state.get("competitor_delta", [])
    brand = state.get("brand", "Unknown")
    industry = state.get("industry", "Unknown")

    avg_score = round(sum(s["score"] for s in scores) / len(scores), 3) if scores else 0.0
    bullish = sum(1 for s in scores if s["label"] == "bullish")
    bearish = sum(1 for s in scores if s["label"] == "bearish")
    fc_30 = forecast[0].get("day_30", {}).get("forecast") if forecast else None

    primary = next((c for c in competitors if c.get("is_primary")), None)
    leader = competitors[0] if competitors else None

    outlook = "stable"
    if avg_score > 0.2:
        outlook = "positive"
    elif avg_score < -0.2:
        outlook = "negative"

    report = (
        f"{brand} in {industry} shows a {outlook} sentiment profile with an average score of "
        f"{avg_score:+.3f} across {len(scores)} headlines ({bullish} bullish, {bearish} bearish). "
    )

    if fc_30 is not None:
        report += f"The 30-day forecast is {fc_30:.1f}. "

    if anomalies:
        report += f"{len(anomalies)} sentiment anomalies were detected, which may signal short-term volatility. "
    else:
        report += "No major sentiment anomalies were detected. "

    if leader and primary:
        if leader["brand"] == primary["brand"]:
            report += f"{brand} currently leads the tracked peer set on sentiment."
        else:
            report += f"{leader['brand']} is currently leading the peer set, so {brand} may need stronger differentiation."

    return report
 
 
if __name__ == "__main__":
    state: AgentState = {
        "industry": "Hotels",
        "brand": "Marriott",
        "headlines": [],
        "sentiment_scores": [
            {"score": 0.6, "label": "bullish"},
            {"score": -0.3, "label": "bearish"},
            {"score": 0.1, "label": "neutral"},
        ],
        "forecast": [{"day_30": {"forecast": 148.5}, "day_90": {"forecast": 162.0}}],
        "anomalies": [{"direction": "drop", "z_score": -2.8}],
        "competitor_delta": [
            {"brand": "Marriott", "score": 0.6, "is_primary": True},
            {"brand": "Hilton",   "score": 0.4, "is_primary": False},
        ],
        "insight_report": "",
    }
    out = insight_agent(state)
    print("\n" + "="*60)
    print(out["insight_report"])
