import asyncio
import base64
import json
import logging
import random

import boto3
import streamlit as st
from strands import tool

logger = logging.getLogger(__name__)

# ── AWS client ────────────────────────────────────────────────────────────────

_bedrock = boto3.client("bedrock-runtime", region_name="us-west-2")


# ── Tool ──────────────────────────────────────────────────────────────────────

@tool
async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """
    Generate an image using Stability AI based on a text description.

    Use this tool when users ask you to create, generate, draw, make, or
    produce images.

    Args:
        prompt: Detailed text description of the image to generate.
        aspect_ratio: Image aspect ratio — '1:1', '16:9', '9:16', etc.

    Returns:
        str: Success message with generation details.
    """
    try:
        seed = random.randint(0, 4294967295)

        request = {
            "prompt":        prompt[:10000],
            "mode":          "text-to-image",
            "aspect_ratio":  aspect_ratio,
            "output_format": "png",
            "seed":          seed,
        }

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: _bedrock.invoke_model(
                modelId="stability.sd3-5-large-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request),
            ),
        )

        response_body = json.loads(response.get("body").read())
        finish_reason = response_body.get("finish_reasons", [None])[0]

        if finish_reason is not None:
            return f"Image generation error: {finish_reason}"

        image_bytes = base64.b64decode(response_body["images"][0])

        if "generated_images" not in st.session_state:
            st.session_state.generated_images = []

        st.session_state.generated_images.append(image_bytes)
        return f"✅ Image generated successfully! (seed: {seed})"

    except Exception as e:
        import traceback
        return f"❌ Error: {str(e)}\n{traceback.format_exc()}"