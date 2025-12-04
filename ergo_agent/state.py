import base64
import json
from typing import TypedDict, List, Dict
from typing_extensions import Annotated
from operator import add
from PIL import Image, UnidentifiedImageError
import io


# ============================================================================
# DATA LOADING
# ============================================================================


with open("activities.json", "r") as f:
    ERGONOMIC_DATA = json.load(f)

with open("products.json", "r") as f:
    PRODUCT_DATA = json.load(f)

# Activity categories for classification
ACTIVITY_CATEGORIES = list(ERGONOMIC_DATA.keys())

# At module level, after PRODUCT_DATA is loaded
PRODUCTS_CATALOG = [
    {
        "id": product.get("id"),
        "name": product.get("name"),
        "description": product.get("description"),
        "category": product.get("category"),
    }
    for product in PRODUCT_DATA.get("ergonomic_products", [])
]

# ============================================================================
# STATE DEFINITION
# ============================================================================

class AgentState(TypedDict):
    """State passed between agents"""
    image_base64: str
    image_path: str
    activity_category: str
    activity_title: str
    scene_context: str
    relevant_checks: List[Dict]
    risk_analysis: List[Dict]
    flagged_risks: List[Dict]
    recommendations: List[Dict]
    overall_risk_level: str
    messages: Annotated[List[str], add]  
    should_skip_ergonomics: bool
    filter_result: Dict | None
    affected_body_regions: List[str]


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
