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

from cmn.tools.tool import calculator, sales_data, generate_image, render_chart, render_chart_payload

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

SYSTEM_PROMPT = """You are a helpful assistant with access to sales data,
an image generator, a calculator, a clock, and a chart renderer.

IMPORTANT: Before using any tool, always explain what you are going to do first.
Examples:
- "I'll calculate that for you…"        → then use calculator
- "Let me check the current time…"      → then use current_time
- "I'll generate an image of [desc]…"   → then use generate_image
- "Let me pull the sales figures for…"  → then use sales_data
- "I'll render that as a chart…"        → then use render_chart

When rendering charts:
- Always fetch data first with sales_data, then call render_chart.
- x_label and y_label must exactly match column names from the data.
- Use month_name for the x axis when charting monthly data.
- For multi-series charts (e.g. comparing two years), add a 'series' column
  to each row to identify the series name. Example:
  [
    {"month_name": "January", "revenue": 205000, "series": "2023"},
    {"month_name": "January", "revenue": 213000, "series": "2024"},
    ...
  ]
  Then set x_label='month_name', y_label='revenue'.

When presenting sales data:
- Use clear markdown tables where helpful.
- Highlight notable trends (best/worst month, YoY changes, dips, recoveries).
- Always provide a short written summary after showing numbers.

Always provide context and explanation before and after using tools."""



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
        tools=[calculator, current_time, generate_image, sales_data, render_chart],
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
                last_tool_name = None
                chart_payloads = []
                async for chunk in agent.stream_async(prompt):

                    # ── Text chunks ───────────────────────────────────────────────
                    #if "data" in chunk:
                    #    response_text += chunk["data"]
                    #    message_placeholder.markdown(response_text + "▌")
                        
                    # # ── Tool starting ─────────────────────────────────────────────
                    # if "current_tool_use" in chunk:
                    #     tool_name = chunk["current_tool_use"].get("name")
                    #     if tool_name and tool_name != last_tool_name:
                    #         last_tool_name = tool_name

                    # # ── Tool complete — result arrives in user-role message ───────
                    # if "message" in chunk:
                    #     msg = chunk["message"]
                    #     if msg.get("role") == "user":
                    #         for block in msg.get("content", []):
                    #             if "toolResult" in block and last_tool_name:
                    #                 status = block["toolResult"].get("status", "unknown")
                    #                 icon   = "✅" if status == "success" else "❌"
                    #                 print(f"{icon} Tool complete: {last_tool_name} ({status})")
                    #                 #status_widget.write(f"{icon} Tool complete: **{last_tool_name}**")
                    #                 last_tool_name = None

                    # ── Tool complete ─────────────────────────────────────────────
                    if "result" in chunk:
                        for tool_name, tool_metrics in chunk["result"].metrics.tool_metrics.items():
                            print(f"✅ Tool complete: {tool_name} "
                                f"calls={tool_metrics.call_count} "
                                f"ok={tool_metrics.success_count} "
                                f"errors={tool_metrics.error_count}")
                            if tool_name == "render_chart":
                                # tool_use.input has the original args passed to the tool
                                tool_input = tool_metrics.tool.get("input", {})
                                if tool_input.get("data"):
                                    chart_payloads.append({
                                        "chart_type": tool_input.get("chart_type"),
                                        "title":      tool_input.get("title"),
                                        "x_label":    tool_input.get("x_label"),
                                        "y_label":    tool_input.get("y_label"),
                                        "data":       tool_input.get("data"),
                                        "color":      tool_input.get("color", ""),
                                    })

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
                return response_text, chart_payloads 

            full_response, chart_payloads  = asyncio.run(stream_response())

            # ── Render charts ─────────────────────────────────────────────────────
            for payload in chart_payloads:
                render_chart_payload(payload, st.container())
                st.session_state.messages.append({
                    "role":    "assistant",
                    "type":    "chart",
                    "text":    full_response,
                    "content": payload,
                })


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