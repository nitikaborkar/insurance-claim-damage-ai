from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    activity_classifier_node,
    filterer_node,
    risk_analyzer_node,
    recommender_node,
)

def route_after_filter(state: AgentState) -> str:
    return "__end__" if state.get("should_skip_ergonomics", False) else "analyzer"

def create_ergonomic_agent_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("classifier", activity_classifier_node)
    workflow.add_node("filterer", filterer_node)
    workflow.add_node("analyzer", risk_analyzer_node)
    workflow.add_node("recommender", recommender_node)

    workflow.add_edge("classifier", "filterer")
    workflow.add_conditional_edges(
        "filterer", route_after_filter, {"analyzer": "analyzer", "__end__": END}
    )
    workflow.add_edge("analyzer", "recommender")
    workflow.add_edge("recommender", END)

    workflow.set_entry_point("classifier")
    
    return workflow.compile()
