from .state import load_and_compress, AgentState
from .graph import create_ergonomic_agent_graph

_graph = create_ergonomic_agent_graph()   # build once at import

def analyze_image_path(image_path: str) -> dict:
    image_base64 = load_and_compress(image_path)
    
    # Initialize state
    initial_state = {
        "image_base64": image_base64,
        "image_path": image_path,
        "activity_category": "",
        "activity_title": "",
        "scene_context": "",
        "relevant_checks": [],
        "risk_analysis": [],
        "flagged_risks": [],
        "recommendations": [],
        "overall_risk_level": None,
        "messages": [], 
        "should_skip_ergonomics": False,
        "filter_result": None,

    }

    final_state = _graph.invoke(initial_state)

    if final_state.get("should_skip_ergonomics"):
        fr = final_state.get("filter_result") or {}
        return {
            "image_path": image_path,
            "activity_category": final_state.get("activity_category", ""),
            "activity_title": final_state.get("activity_title", ""),
            "scene_context": final_state.get("scene_context", ""),
            "skipped": True,
            "skip_reason": fr.get("reason", "Image not suitable for ergonomic assessment."),
            "risk_analysis": [],
            "observed_risks": [],
            "recommendations": [],
            "overall_risk_level": None,
        }
    
    rec = final_state["recommendations"][0]
    return {
            "image_path": image_path,
            "activity_category": final_state["activity_category"],
            "activity_title": final_state["activity_title"],
            "scene_context": final_state.get("scene_context", ""),
            "skipped": False,
            "skip_reason": None,
            "risk_analysis": final_state["risk_analysis"],
            "observed_risks": rec.get("observed_risks", []),
            "recommendations": rec.get("recommendations", []),
            "overall_risk_level": rec.get("overall_risk_level", None),
        }