from typing import TypedDict
from langgraph.graph import add_messages
from typing_extensions import Annotated
import json
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import io
import base64

# Load vehicle damage types and claim actions
DAMAGE_TYPES_PATH =  "vehicle_damage_types.json"
CLAIM_ACTIONS_PATH = "claim_actions.json"

with open(DAMAGE_TYPES_PATH) as f:
    VEHICLE_DAMAGE_DATA = json.load(f)

with open(CLAIM_ACTIONS_PATH) as f:
    CLAIM_ACTIONS_CATALOG = json.load(f).get("claim_actions", [])

DAMAGE_CATEGORIES = list(VEHICLE_DAMAGE_DATA.keys())


class AgentState(TypedDict):
    """State for vehicle damage claim assessment workflow"""
    
    # Input
    image_base64: str
    
    # Classification results
    damage_category: str  # e.g., "FRONT_END_COLLISION"
    damage_description: str  # e.g., "Front bumper collision damage"
    incident_context: str  # e.g., "vehicle front-end collision"
    
    # Validation results
    filter_result: dict  # {"validity": "VALID/INVALID", "reason": "...", "notes": "..."}
    should_skip_assessment: bool  # If True, skip damage analysis
    
    # Damage analysis results
    relevant_checks: list  # List of damage checks for this category
    damage_analysis: list  # Detailed damage assessment results
    flagged_damages: list  # Damages that are actually present
    
    # Claim decision results
    claim_recommendations: list  # Claim decision and recommendations
    affected_areas: list  # List of damaged vehicle areas
    overall_severity_level: str  # "LOW" / "MEDIUM" / "HIGH"
    estimated_total_cost: str  # e.g., "$2,500-$4,000"
    fraud_indicators: list  # Any red flags detected
    
    # Action recommendations
    action_recommendations: list  # Recommended next steps from claim_actions
    action_selection_reasoning: str  # Why these actions were chosen
    
    # Workflow tracking
    messages: Annotated[list[str], add_messages]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_and_compress(image_path, max_size_kb=4800, max_dimension=2048):
    """
    Load and compress an image safely with decompression bomb protection.

    Args:
        image_path: Path to image file
        max_size_kb: Maximum output size in KB (default 4.8MB for Anthropic)
        max_dimension: Maximum width/height in pixels (default 2048)

    Returns:
        Base64-encoded JPEG string

    Raises:
        ValueError: If image is invalid or too large
        UnidentifiedImageError: If file is not a valid image
    """
    
    # Set decompression bomb protection
    # Default is 178M pixels; we reduce to ~89M (~9000x9900 max)
    Image.MAX_IMAGE_PIXELS = 89_000_000

    try:
        # Open and verify the image
        img = Image.open(image_path)
        img.verify()  # Check it's not corrupted
        
        # Re-open after verify() (verify closes the file)
        img = Image.open(image_path)
        
    except UnidentifiedImageError:
        raise ValueError("File is not a valid image")
    except Image.DecompressionBombError:
        raise ValueError("Image is too large (possible decompression bomb)")
    except Exception as e:
        raise ValueError(f"Failed to open image: {str(e)}")

    # Check dimensions before processing
    if img.width > max_dimension or img.height > max_dimension:
        raise ValueError(
            f"Image dimensions ({img.width}x{img.height}) exceed "
            f"maximum ({max_dimension}x{max_dimension})"
        )

    # Convert problematic modes to RGB for JPEG
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        # Create white background for transparency
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "P":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
        img = background
    elif img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize large images while maintaining aspect ratio
    img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

    # Try progressive compression with safety limits
    max_attempts = 5
    quality = 85
    quality_step = 15

    for attempt in range(max_attempts):
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        data = buffer.getvalue()

        # Success - under size limit
        if len(data) <= max_size_kb * 1024:
            return base64.b64encode(data).decode("utf-8")

        # Reduce quality for next attempt
        quality -= quality_step
        
        # Last resort: reduce dimensions further
        if quality < 20:
            current_width, current_height = img.size
            new_width = int(current_width * 0.8)
            new_height = int(current_height * 0.8)
            
            if new_width < 100 or new_height < 100:
                # Image is too small to compress further
                break
                
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            quality = 50  # Reset quality after resize

    # Failed to compress adequately
    raise ValueError(
        f"Image could not be compressed below {max_size_kb}KB "
        f"after {max_attempts} attempts"
    )
