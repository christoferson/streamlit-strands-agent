import asyncio
import base64
import json
import random
from io import BytesIO

import boto3
import streamlit as st
from PIL import Image
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import current_time

from cmn.tools.tool import calculator, sales_data, generate_image

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Strands Chat App",
    page_icon="💬",
    layout="centered",
)

# ── AWS clients ───────────────────────────────────────────────────────────────

bedrock_runtime          = boto3.client("bedrock-runtime", region_name="us-east-1")
bedrock_runtime_us_west_2 = boto3.client("bedrock-runtime", region_name="us-west-2")


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant with access to sales data, \
an image generator, a calculator, and a clock.

IMPORTANT: Before using any tool, always explain what you are going to do first.
Examples:
- "I'll calculate that for you…"        → then use calculator
- "Let me check the current time…"      → then use current_time
- "I'll generate an image of [desc]…"   → then use generate_image
- "Let me pull the sales figures for…"  → then use sales_data

When presenting sales data:
- Use clear markdown tables where helpful.
- Highlight notable trends (best/worst month, YoY changes, dips, recoveries).
- Always provide a short written summary after showing numbers.

Always provide context and explanation before and after using tools."""


# ── Image generation tool ─────────────────────────────────────────────────────

# @tool
# async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
#     """
#     Generate an image using Stability AI based on a text description.

#     Use this tool when users ask you to create, generate, draw, make, or
#     produce images.

#     Args:
#         prompt: Detailed text description of the image to generate.
#         aspect_ratio: Image aspect ratio — '1:1', '16:9', '9:16', etc.

#     Returns:
#         str: Success message with generation details.
#     """
#     try:
#         seed = random.randint(0, 4294967295)

#         request = {
#             "prompt":        prompt[:10000],
#             "mode":          "text-to-image",
#             "aspect_ratio":  aspect_ratio,
#             "output_format": "png",
#             "seed":          seed,
#         }

#         loop = asyncio.get_event_loop()
#         response = await loop.run_in_executor(
#             None,
#             lambda: bedrock_runtime_us_west_2.invoke_model(
#                 modelId="stability.sd3-5-large-v1:0",
#                 contentType="application/json",
#                 accept="application/json",
#                 body=json.dumps(request),
#             ),
#         )

#         response_body = json.loads(response.get("body").read())
#         finish_reason = response_body.get("finish_reasons", [None])[0]

#         if finish_reason is not None:
#             return f"Image generation error: {finish_reason}"

#         image_bytes = base64.b64decode(response_body["images"][0])

#         if "generated_images" not in st.session_state:
#             st.session_state.generated_images = []

#         st.session_state.generated_images.append(image_bytes)
#         return f"✅ Image generated successfully! (seed: {seed})"

#     except Exception as e:
#         import traceback
#         return f"❌ Error: {str(e)}\n{traceback.format_exc()}"


# ── Agent (cached) ────────────────────────────────────────────────────────────

@st.cache_resource
def initialize_agent() -> Agent:
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        temperature=0.1,
    )

    return Agent(
        model=bedrock_model,
        system_prompt=SYSTEM_PROMPT,
        tools=[calculator, current_time, generate_image, sales_data],
    )


agent = initialize_agent()


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("💬 Strands Chat App")
st.caption("Powered by Claude Sonnet 4 · Stability AI · Sales Analytics")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# ── Chat history ──────────────────────────────────────────────────────────────

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            if message.get("text"):
                st.markdown(message["text"])
            st.image(message["content"], width="stretch")
        else:
            st.markdown(message["content"])

# ── Chat input ────────────────────────────────────────────────────────────────

if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()

        try:
            images_before = len(st.session_state.generated_images)

            async def stream_response() -> str:
                response_text = ""
                async for chunk in agent.stream_async(prompt):
                    if isinstance(chunk, str):
                        response_text += chunk
                        message_placeholder.markdown(response_text + "▌")
                    elif isinstance(chunk, dict):
                        event = chunk.get("event", {})
                        if "contentBlockDelta" in event:
                            delta = event["contentBlockDelta"].get("delta", {})
                            if "text" in delta:
                                response_text += delta["text"]
                                message_placeholder.markdown(response_text + "▌")
                        elif "text" in event:
                            response_text += event["text"]
                            message_placeholder.markdown(response_text + "▌")

                message_placeholder.markdown(response_text)
                return response_text

            full_response = asyncio.run(stream_response())

            images_after = len(st.session_state.generated_images)

            if images_after > images_before:
                for i in range(images_before, images_after):
                    image = Image.open(
                        BytesIO(st.session_state.generated_images[i])
                    )
                    st.image(image, width="stretch")
                    st.session_state.messages.append({
                        "role":    "assistant",
                        "type":    "image",
                        "text":    full_response,
                        "content": image,
                    })
            else:
                st.session_state.messages.append({
                    "role":    "assistant",
                    "content": full_response,
                })

        except Exception as e:
            import traceback
            error_message = f"Error: {str(e)}"
            st.error(error_message)
            st.code(traceback.format_exc())
            st.session_state.messages.append({
                "role":    "assistant",
                "content": error_message,
            })

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.header("Chat Controls")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.cache_resource.clear()
        st.rerun()

    st.metric("Messages",         len(st.session_state.messages))
    st.metric("Images Generated", len(st.session_state.generated_images))

    st.divider()

    st.subheader("Model Info")
    st.text("Chat:   Claude Sonnet 4")
    st.text("Image:  SD 3.5 Large")
    st.text("Region: us-east-1 / us-west-2")

    st.divider()

    st.subheader("Available Tools")
    st.text("📊 Sales Data Analytics")
    st.text("🎨 Image Generation")
    st.text("🧮 Calculator")
    st.text("🕐 Current Time")

    st.divider()

    with st.expander("📊 Sales Data Info"):
        st.markdown("""
        **Dataset:** 2023 & 2024 monthly sales
        **Regions:** North, South
        **Categories:** Electronics, Accessories
        **Metrics:** Revenue, Units, Returns,
        Gross Profit, Margin, Net Revenue
        """)

    st.divider()

    with st.expander("🔍 Debug"):
        if hasattr(agent, "tool_names"):
            st.write("Agent tools:", agent.tool_names)

    st.divider()

    with st.expander("💡 Example Prompts"):
        st.markdown("""
        **Sales queries:**
        - Show me monthly sales for 2024
        - Compare 2023 vs 2024 revenue
        - What was the best month in 2023?
        - Show Electronics sales in the North for 2024
        - Why did sales dip in mid-2024?
        - Break down June 2024 by region

        **Other tools:**
        - Generate an image of Tokyo
        - What is 1234 × 5678?
        - What time is it?
        """)