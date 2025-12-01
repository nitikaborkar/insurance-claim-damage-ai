from .state import load_and_compress, AgentState
from .graph import create_ergonomic_agent_graph

_graph = create_ergonomic_agent_graph()   # build once at import

def analyze_image_path(image_path: str) -> dict:
    image_base64 = load_and_compress(image_path)
    initial_state: AgentState = {
        "image_base64": image_base64,
        "image_path": image_path,
        "activity_category": "",
        "relevant_checks": [],
        "risk_analysis": [],
        "flagged_risks": [],
        "recommendations": [],
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
            "skipped": True,
            "skip_reason": fr.get("reason", "Image not suitable for ergonomic assessment."),
            "risk_analysis": [],
            "recommendations": [],
        }

    return {
        "image_path": image_path,
        "activity_category": final_state["activity_category"],
        "skipped": False,
        "skip_reason": None,
        "risk_analysis": [
            {
                "cue": item["cue"],
                "present": item["present"],
                "observation": item["observation"],
            }
            for item in final_state["risk_analysis"]
        ],
        "recommendations": final_state["recommendations"],
    }
