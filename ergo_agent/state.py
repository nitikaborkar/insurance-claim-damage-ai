import base64
import json
from typing import TypedDict, List, Dict
from typing_extensions import Annotated
from operator import add
from PIL import Image
import io

# ============================================================================
# DATA LOADING
# ============================================================================


with open("activities.json", "r") as f:
    ERGONOMIC_DATA = json.load(f)

# Activity categories for classification
ACTIVITY_CATEGORIES = list(ERGONOMIC_DATA.keys())

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State passed between agents"""
    image_base64: str
    image_path: str
    activity_category: str
    relevant_checks: List[Dict]
    risk_analysis: List[Dict]
    flagged_risks: List[Dict]
    recommendations: List[Dict]
    messages: Annotated[List[str], add]  # For logging
    should_skip_ergonomics: bool          # <-- add this
    filter_result: Dict | None            # optional but useful


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_and_compress(image_path, max_size_kb=4800):
    img = Image.open(image_path)

    # Convert RGBA / LA / P with alpha to RGB for JPEG
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGB")

    # Resize large images (e.g., max dimension 1024px)
    img.thumbnail((1024, 1024))

    # Save to buffer with compression
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    data = buffer.getvalue()

    # Keep compressing until under limit
    while len(data) > max_size_kb * 1024:
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        data = buffer.getvalue()

    return base64.b64encode(data).decode("utf-8")