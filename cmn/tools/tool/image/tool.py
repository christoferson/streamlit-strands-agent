"""
Image Generation Tool - Strands agent interface (UI agnostic).

This tool wraps the ImageService and returns pure data (no UI elements).
"""

import json
import logging

from strands import tool

from .service import ImageService

logger = logging.getLogger(__name__)

# Initialize service
_image_service = ImageService()


@tool
async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """
    Generate an image using Stability AI based on a text description.

    Use this tool when users ask you to create, generate, draw, make, or
    produce images.

    Args:
        prompt: Detailed text description of the image to generate.
        aspect_ratio: Image aspect ratio - '1:1', '16:9', '9:16', etc.

    Returns:
        str: JSON string with generation result:
        {
            "status": "success" | "error",
            "image_bytes_b64": str (base64 encoded if success),
            "seed": int (if success),
            "prompt": str (if success),
            "aspect_ratio": str (if success),
            "error": str (if error)
        }
    """
    logger.info("generate_image tool called: prompt_length=%d", len(prompt))

    result = await _image_service.generate(prompt, aspect_ratio)

    # Convert image_bytes to base64 for JSON serialization
    if result.get("status") == "success":
        import base64
        result["image_bytes_b64"] = base64.b64encode(result["image_bytes"]).decode("utf-8")
        del result["image_bytes"]

    return json.dumps(result)
