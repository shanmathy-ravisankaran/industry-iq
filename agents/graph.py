from langgraph.graph import StateGraph, END
from agents.sentiment_agent  import AgentState, sentiment_agent
from agents.forecasting_agent import forecasting_agent
from agents.anomaly_agent    import anomaly_agent
from agents.competitor_agent import competitor_agent
from agents.insight_agent    import insight_agent
 
 
def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
 
    # ── Register all nodes ───────────────────────────────────────
    graph.add_node("sentiment",   sentiment_agent)
    graph.add_node("forecasting", forecasting_agent)
    graph.add_node("anomaly",     anomaly_agent)
    graph.add_node("competitor",  competitor_agent)
    graph.add_node("insight",     insight_agent)
 
    # ── Entry point ──────────────────────────────────────────────
    graph.set_entry_point("sentiment")
 
    # ── After sentiment → fan out to 3 agents in sequence ────────
    # LangGraph runs nodes sequentially; we chain them so each
    # receives the accumulated state from the previous node.
    graph.add_edge("sentiment",   "forecasting")
    graph.add_edge("forecasting", "anomaly")
    graph.add_edge("anomaly",     "competitor")
 
    # ── Fan-in: all results flow into the insight agent ──────────
    graph.add_edge("competitor",  "insight")
    graph.add_edge("insight",     END)
 
    return graph.compile()
 
 
# ── Convenience runner ────────────────────────────────────────────
def run_pipeline(
    industry: str = "Hotels",
    brand:    str = "Marriott",
    headlines: list[str] | None = None,
) -> AgentState:
 
    app = build_graph()
 
    initial_state: AgentState = {
        "industry":        industry,
        "brand":           brand,
        "headlines":       headlines or [],
        "sentiment_scores":  [],
        "forecast":          [],
        "anomalies":         [],
        "competitor_delta":  [],
        "insight_report":    "",
    }
 
    print(f"\n{'='*55}")
    print(f"  IndustryIQ pipeline — {industry} / {brand}")
    print(f"{'='*55}\n")
 
    result = app.invoke(initial_state)
 
    print(f"\n{'='*55}")
    print("  PIPELINE COMPLETE")
    print(f"{'='*55}")
    print(f"  Sentiment scores : {len(result['sentiment_scores'])}")
    print(f"  Anomalies found  : {len(result['anomalies'])}")
    print(f"  Competitors ranked: {len(result['competitor_delta'])}")
    print(f"\n  INSIGHT REPORT:\n")
    print(result["insight_report"])
    print(f"{'='*55}\n")
 
    return result
 
 
if __name__ == "__main__":
    run_pipeline(industry="Hotels", brand="Marriott")
