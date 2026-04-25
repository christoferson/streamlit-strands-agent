"""
Image Generation Service - Pure business logic for AI image generation.

This module contains NO UI dependencies and can be used from any interface.
"""

import asyncio
import base64
import json
import logging
import random
from typing import Dict, Any

import boto3

logger = logging.getLogger(__name__)


class ImageService:
    """Pure business logic for image generation - UI agnostic."""

    def __init__(self, region_name: str = "us-west-2"):
        """Initialize service with AWS Bedrock client."""
        self._bedrock = boto3.client("bedrock-runtime", region_name=region_name)
        logger.info("ImageService initialized with region %s", region_name)

    async def generate(
        self,
        prompt: str,
        aspect_ratio: str = "1:1"
    ) -> Dict[str, Any]:
        """
        Generate an image using Stability AI based on a text description.

        Args:
            prompt: Detailed text description of the image to generate
            aspect_ratio: Image aspect ratio ('1:1', '16:9', '9:16', etc.)

        Returns:
            Dictionary with generation result:
            {
                "status": "success" | "error",
                "image_bytes": bytes (if success),
                "seed": int (if success),
                "error": str (if error)
            }
        """
        logger.info("Generating image: prompt_length=%d aspect_ratio=%s",
                   len(prompt), aspect_ratio)

        try:
            seed = random.randint(0, 4294967295)

            request = {
                "prompt": prompt[:10000],
                "mode": "text-to-image",
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
                "seed": seed,
            }

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._bedrock.invoke_model(
                    modelId="stability.sd3-5-large-v1:0",
                    contentType="application/json",
                    accept="application/json",
                    body=json.dumps(request),
                ),
            )

            response_body = json.loads(response.get("body").read())
            finish_reason = response_body.get("finish_reasons", [None])[0]

            if finish_reason is not None:
                return {
                    "status": "error",
                    "error": f"Image generation error: {finish_reason}"
                }

            image_bytes = base64.b64decode(response_body["images"][0])

            return {
                "status": "success",
                "image_bytes": image_bytes,
                "seed": seed,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio
            }

        except Exception as e:
            logger.error("Image generation failed: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "error": f"Image generation failed: {str(e)}"
            }
