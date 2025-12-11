from langgraph.graph import StateGraph, END
from car_agent.state import AgentState
from car_agent.nodes import (
    damage_classifier_node,
    filterer_node,
    damage_analyzer_node,
    claim_decision_node,
    action_recommender_node
)

def should_skip_assessment(state: AgentState) -> str:
    """Router: Skip assessment if photo invalid"""
    if state.get("should_skip_assessment", False):
        return "end"
    return "analyze_damage"

def build_graph():
    """Build the vehicle damage claim assessment workflow"""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("classify_damage", damage_classifier_node)
    workflow.add_node("validate_photo", filterer_node)
    workflow.add_node("analyze_damage", damage_analyzer_node)
    workflow.add_node("make_claim_decision", claim_decision_node)
    workflow.add_node("recommend_actions", action_recommender_node)
    
    # Define flow
    workflow.set_entry_point("classify_damage")
    workflow.add_edge("classify_damage", "validate_photo")
    workflow.add_conditional_edges(
        "validate_photo",
        should_skip_assessment,
        {
            "analyze_damage": "analyze_damage",
            "end": END
        }
    )
    workflow.add_edge("analyze_damage", "make_claim_decision")
    workflow.add_edge("make_claim_decision", "recommend_actions")
    workflow.add_edge("recommend_actions", END)
    
    return workflow.compile()
