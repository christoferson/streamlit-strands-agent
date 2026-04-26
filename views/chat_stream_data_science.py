import asyncio
import base64
import json
import random
from io import BytesIO

import boto3
import streamlit as st
from PIL import Image
from strands import Agent, tool
from strands.plugins import Plugin, hook
from strands.hooks import BeforeToolCallEvent, AfterToolCallEvent
from strands.models import BedrockModel
#from strands_tools import current_time

# Tool registry and base classes
from cmn.tools.tool.base import ToolRegistry
from cmn.tools.tool.image.image_tool import ImageTool, ImageResponse

from cmn.tools.tool.calculator import CalculatorTool
from cmn.tools.tool.sales_data import SalesDataTool
from cmn.tools.tool.chart import ChartTool

# Old renderers (will be removed after migration)
from views.tools.tool.base import RendererRegistry
from views.tools.tool.pdf import PdfRenderer
from views.tools.tool.chart import ChartRenderer
from views.tools.tool.calculator import CalculatorRendererStreamlit


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Strands Chat App",
    page_icon="🤖",
    layout="centered",
)

# ── AWS clients ───────────────────────────────────────────────────────────────

bedrock_runtime          = boto3.client("bedrock-runtime", region_name="us-east-1")
bedrock_runtime_us_west_2 = boto3.client("bedrock-runtime", region_name="us-west-2")


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant with access to sales data,
an image generator, a calculator, a clock, a chart renderer, and a PDF report generator.

CRITICAL RULES - READ CAREFULLY:
1. Only use tools when EXPLICITLY requested by the user
2. Do NOT create PDFs unless user EXPLICITLY uses the word "PDF", "report", "download", "file", or "save"
3. Do NOT create charts unless user EXPLICITLY uses the word "chart", "graph", "visualize", "plot", or "draw"
4. When user asks to "show" or "display" or "get" data, ONLY use sales_data and present as TEXT/TABLE
5. Default behavior is ALWAYS text/table display - never PDF or chart unless explicitly requested

WHAT NOT TO DO:
- User asks "show me 2024 data" → Do NOT create PDF! Just show table.
- User asks "display 2023 sales" → Do NOT create chart! Just show table.
- User asks "get 2024 numbers" → Do NOT create PDF or chart! Just show table.
- User asks "what are 2024 sales" → Do NOT create anything! Just show table.

Tool Usage Guidelines:
- generate_image: ONLY when user explicitly asks for an image/picture/photo/visual
- calculator: ONLY when user explicitly asks to calculate/compute/add/multiply numbers
- current_time: ONLY when user explicitly asks for the time/date/now
- sales_data: When user asks about sales/revenue/data/numbers (for display as text)
- render_chart: FORBIDDEN unless user explicitly says "chart", "graph", "plot", "visualize", or "draw"
- generate_pdf_report: FORBIDDEN unless user explicitly says "PDF", "report", "download", "file", or "save"

DEFAULT BEHAVIOR (99% of queries):
When user says "show", "display", "get", "what are", "tell me", "fetch", etc:
1. Call sales_data to fetch the data
2. Display as markdown table with text summary
3. STOP - Do NOT create PDF or chart
4. Wait for next user instruction

ONLY create PDF or chart if user EXPLICITLY requests it in a separate message.

IMPORTANT: Before using any tool, briefly explain what you're about to do.

Examples:
- User: "Generate an image of Tokyo" → "I'll generate an image..." → use generate_image ONLY
- User: "What's 123 * 456?" → "I'll calculate that..." → use calculator ONLY
- User: "Show me 2024 sales" → "Let me fetch the 2024 sales data..." → use sales_data(year=2024) ONLY, display as table
- User: "Show me 2024 sales in a chart" → use sales_data(year=2024) + render_chart
- User: "Create a PDF of 2024 sales" → use sales_data(year=2024) + generate_pdf_report
- User: "What were the best months in 2023?" → use sales_data(year=2023) ONLY, answer with text

CORRECT Multi-turn example:
Turn 1:
  User: "Show me 2023 sales"
  You: Call sales_data(year=2023), display table, STOP
Turn 2:
  User: "Now show 2024"
  You: Call sales_data(year=2024), display table, STOP
Turn 3:
  User: "Create a PDF of 2024 sales"
  You: Call sales_data(year=2024) AGAIN (fresh fetch), then generate_pdf_report with fresh data

WRONG Examples - DO NOT DO THIS:
Turn 1:
  User: "Show me 2024 data"
  You: Call sales_data(year=2024), create PDF ← WRONG! User did not ask for PDF!
  Correct: Just show table, no PDF

Turn 2:
  User: "Show me 2023 sales" (earlier in conversation)
  User: "Create 2024 PDF" (now)
  You: Use 2023 data for PDF ← WRONG! Must fetch fresh 2024 data!
  Correct: Call sales_data(year=2024) first, then create PDF with that data

When rendering charts (ONLY if explicitly requested):
- Fetch data with sales_data first, then call render_chart
- x_label and y_label must exactly match column names from the data
- Use month_name for the x axis when charting monthly data
- For multi-series charts, add a 'series' column:
  [{"month_name": "January", "revenue": 205000, "series": "2023"}, ...]

When presenting sales data (without chart/PDF):
- Use clear markdown tables
- Highlight notable trends (best/worst month, YoY changes, dips, recoveries)
- Provide a short written summary after showing numbers
- Stop there - do NOT create charts or PDFs unless explicitly asked

When generating PDF reports (FORBIDDEN unless explicitly requested):
- User MUST explicitly say "PDF", "report", "download", "file", or "save"
- ALWAYS fetch fresh data with sales_data first using correct year parameter
- NEVER reuse data from previous queries - always call sales_data again
- If user asks for "2024 PDF", call sales_data(query_type="get_monthly_sales", year=2024)
- If user previously showed 2023 data, ignore it - fetch fresh 2024 data
- Pass the NEWLY FETCHED data to generate_pdf_report (not old data)
- Include a meaningful summary parameter
- Stop after generating PDF

When generating charts (FORBIDDEN unless explicitly requested):
- User MUST explicitly say "chart", "graph", "plot", "visualize", or "draw"
- ALWAYS fetch fresh data with sales_data first using correct year parameter
- NEVER reuse data from previous queries - always call sales_data again
- Pass the NEWLY FETCHED data to render_chart (not old data)

Key principle: ONE tool per request unless user explicitly asks for multiple things.

CRITICAL DATA FRESHNESS RULE:
- ALWAYS fetch fresh data before creating PDF or chart
- NEVER reuse data from earlier in the conversation
- Each PDF/chart request requires NEW sales_data call with correct parameters
- Example: If user asks "create 2024 PDF" after showing 2023 data:
  1. Call sales_data(year=2024) - get fresh 2024 data
  2. Call generate_pdf_report with the 2024 data
  Do NOT use the 2023 data from earlier in conversation!

REMEMBER:
- "Show me X" = fetch data + display as text/table ONLY
- "Chart X" or "Graph X" = fetch fresh data + render_chart
- "PDF of X" or "Report of X" = fetch fresh data + generate_pdf_report

FINAL ENFORCEMENT RULES:
1. If user message does NOT contain "PDF"/"report"/"download"/"file"/"save" → NO PDF
2. If user message does NOT contain "chart"/"graph"/"plot"/"visualize"/"draw" → NO CHART
3. Before calling generate_pdf_report, ALWAYS call sales_data with correct year FIRST
4. Before calling render_chart, ALWAYS call sales_data with correct year FIRST
5. NEVER pass old/cached/previous data to PDF or chart tools
6. When in doubt, just show table - do NOT create PDF or chart

If the user's request is ambiguous, ask for clarification rather than using tools proactively.
Never combine chart + PDF unless explicitly requested in same message.

Your default mode is: fetch data → show table → wait for next instruction."""


##---

# Initialize old renderers (for PDF/Chart until they're migrated)
pdf_renderer = PdfRenderer()

renderer_registry = RendererRegistry()
renderer_registry.register("calculator", CalculatorRendererStreamlit())
renderer_registry.register("render_chart", ChartRenderer())

tool_registry = ToolRegistry()
tool_registry.register("calculator", CalculatorTool())
tool_registry.register("sales_data", SalesDataTool())
tool_registry.register("render_chart", ChartTool())


def log_after(event: AfterToolCallEvent) -> None:

    tool_name = event.tool_use['name']
    print(f"Completed: {event.tool_use['name']}")



    # Try to render with registered renderer
    renderer = renderer_registry.get(tool_name)
    if renderer:
        #renderer.render(result_data, st.container())
        print(f"DEBUG: Found renderer for tool '{tool_name}' - rendering result")
    else:
        print(f"No renderer registered for tool '{tool_name}' - skipping rendering")

    
# ── Agent (cached) ────────────────────────────────────────────────────────────

def initialize_agent() -> Agent:
    """Initialize agent - NOT cached to maintain fresh state per session."""
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        temperature=0.0,  # Zero temperature for strict instruction following
    )

    agent =  Agent(
        model=bedrock_model,
        system_prompt=SYSTEM_PROMPT,
        #tools=[calculator, current_time, sales_data, render_chart, generate_pdf_report],
        tools=[
            tool_registry.get("calculator").execute,
            tool_registry.get("sales_data").execute,
            tool_registry.get("render_chart").execute,
        ]
    )

    agent.add_hook(log_after, AfterToolCallEvent)

    return agent


# Initialize agent once per session (not per page load)
if "agent" not in st.session_state:
    st.session_state.agent = initialize_agent()

agent = st.session_state.agent

# Image uses registry - no initialization needed, already registered in tool_new.py


# ── UI ────────────────────────────────────────────────────────────────────────

st.title("Strands Chat App")
st.caption("Powered by Claude Sonnet 4 · Stability AI · Sales Analytics")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

if "generated_pdfs" not in st.session_state:
    st.session_state.generated_pdfs = []

# ── Chat history ──────────────────────────────────────────────────────────────

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            if message.get("text"):
                st.markdown(message["text"])
            # Image content is now a dict with metadata, bytes are in session state
            content = message["content"]
            if isinstance(content, dict) and content.get("image_stored"):
                # Retrieve from session state
                image_index = content.get("image_index", 0)
                if image_index < len(st.session_state.generated_images):
                    image_bytes = st.session_state.generated_images[image_index]
                    prompt = content.get("prompt", "")
                    seed = content.get("seed", "")
                    st.success(f"Image generated successfully (seed: {seed})")
                    st.image(image_bytes, caption=prompt[:100], width="stretch")
                    with st.expander("Generation Details"):
                        st.write(f"**Seed:** {seed}")
                        st.write(f"**Aspect Ratio:** {content.get('aspect_ratio', '1:1')}")
                        st.write(f"**Prompt:** {prompt}")
                else:
                    st.warning("Image data not found in session")
            else:
                # Legacy format (PIL Image object)
                st.image(content, width="stretch")
        elif message.get("type") == "pdf":
            if message.get("text"):
                st.markdown(message["text"])
            pdf_renderer.render(message["content"], st.container())
        elif message.get("type") == "chart":
            if message.get("text"):
                st.markdown(message["text"])
            chart_renderer.render(message["content"], st.container())
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
            async def stream_response() -> str:
                response_text = ""
                #tool_names_map = {}
                chart_payloads = []
                pdf_payloads = []
                image_payloads = []
                current_tool_renderer = None
                current_tool_result = None

                async for chunk in agent.stream_async(prompt):

                    if isinstance(chunk, dict):
                        print(f"DEBUG CHUNK KEYS: {chunk.keys()}")

                        # Check for tool use information
                        if "current_tool_use" in chunk:
                            current_tool_use = chunk.get("current_tool_use", {})
                            current_tool_name = current_tool_use.get('name')
                            print(f"DEBUG current_tool_use: {current_tool_use}")
                            current_tool_renderer = renderer_registry.get(current_tool_name)

                        # Check for tool results
                        if "tool_result" in chunk:
                            print(f"DEBUG tool_result chunk: {chunk}")

                        if "tool_output" in chunk:
                            print(f"DEBUG tool_output chunk: {chunk}")


                    # Track tool use blocks
                    if isinstance(chunk, dict) and "event" in chunk:
                        event = chunk["event"]

                        # Tool use starts
                        if "contentBlockStart" in event:
                            start_block = event["contentBlockStart"]
                            #print(f"DEBUG contentBlockStart: {start_block}")
                            if "toolUse" in start_block:
                                tool_use = start_block["toolUse"]
                                tool_use_id = tool_use.get("toolUseId")
                                tool_name = tool_use.get("name")
                                if tool_use_id and tool_name:
                                    tool_names_map[tool_use_id] = tool_name
                                    print(f"DEBUG: Captured tool mapping - {tool_use_id} -> {tool_name}")
                                    #print(f"{tool_names_map}")
                                    tool_registry.get(tool_name),
                                else:
                                    print(f"DEBUG: Missing tool_use_id or tool_name: {tool_use}")

                        # Text chunks
                        if "contentBlockDelta" in event:
                            delta = event["contentBlockDelta"].get("delta", {})
                            if "text" in delta:
                                response_text += delta["text"]
                                message_placeholder.markdown(response_text + "▌")
                        elif "text" in event:
                            response_text += event["text"]
                            message_placeholder.markdown(response_text + "▌")

                    # String chunks
                    elif isinstance(chunk, str):
                        response_text += chunk
                        message_placeholder.markdown(response_text + "▌")

                    # Check for message chunks that contain tool results
                    if isinstance(chunk, dict) and "message" in chunk:
                        msg = chunk["message"]
                        print(f"DEBUG MESSAGE: role={msg.get('role')}, content_keys={msg.keys()}")
                        print(f"DEBUG MESSAGE FULL: {msg}")

                        if msg.get("role") == "user":
                            # User messages contain tool results
                            for block in msg.get("content", []):
                                print(f"DEBUG BLOCK: {block}")
                                if isinstance(block, dict) and "toolResult" in block:
                                    tool_use_id = block.get("toolUseId")
                                    

                                    # Extract content
                                    tool_result = block["toolResult"]
                                    #print(f"DEBUG: tool_result content keys: {tool_result.keys()}")
                                    if "content" in tool_result:
                                        #print(f"DEBUG: tool_result['content']: {tool_result['content']}")
                                        for content_item in tool_result["content"]:
                                            #print(f"DEBUG: content_item: {content_item}")
                                            if isinstance(content_item, dict) and "text" in content_item:
                                                result_text = content_item["text"]
                                                #print(f"DEBUG: Extracted result_text: {result_text[:200]}")

                                                try:
                                                    # Parse the JSON result
                                                    current_tool_result = json.loads(result_text)
                                                    #print(f"DEBUG: Parsed current_tool_result: {current_tool_result}")
                                                except json.JSONDecodeError:
                                                    print(f"DEBUG: Failed to parse tool result JSON: {result_text}")


                message_placeholder.markdown(response_text)

                # Render the tool result if we have both renderer and result
                print(f"DEBUG: Before render - current_tool_renderer={current_tool_renderer}, current_tool_result={current_tool_result}")
                if current_tool_renderer and current_tool_result:
                    print(f"DEBUG: Calling renderer.render() with result: {current_tool_result}")
                    current_tool_renderer.render(current_tool_result, st.container())
                else:
                    print(f"DEBUG: Skipping render - renderer is None: {current_tool_renderer is None}, result is None: {current_tool_result is None}")

                return response_text, chart_payloads, pdf_payloads, image_payloads

            full_response, chart_payloads, pdf_payloads, image_payloads = asyncio.run(stream_response())

            # Debug output
            #st.write(f"DEBUG: Captured {len(image_payloads)} image payloads")
            #if image_payloads:
            #    st.write("DEBUG: First image payload:", image_payloads[0])

            # ── Render charts ─────────────────────────────────────────────────────
            for payload in chart_payloads:
                chart_renderer.render(payload, st.container())
                st.session_state.messages.append({
                    "role":    "assistant",
                    "type":    "chart",
                    "text":    full_response,
                    "content": payload,
                })

            # ── Render PDFs ───────────────────────────────────────────────────────
            for payload in pdf_payloads:
                pdf_renderer.render(payload, st.container())
                st.session_state.messages.append({
                    "role":    "assistant",
                    "type":    "pdf",
                    "text":    full_response,
                    "content": payload,
                })

            # ── Render Images ─────────────────────────────────────────────────
            for payload in image_payloads:
                # Parse response and render
                response = ImageResponse(**payload)
                image_tool = ImageTool()
                image_tool.render(response, st.container())

                st.session_state.messages.append({
                    "role":    "assistant",
                    "type":    "image",
                    "text":    full_response,
                    "content": payload,
                })

            # Add text-only message if no payloads were generated
            if not chart_payloads and not pdf_payloads and not image_payloads:
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

    # Clear chat and reset agent
    if st.button("Clear Chat", width='stretch'):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.session_state.generated_pdfs = []
        st.session_state.agent = initialize_agent()  # Reset agent conversation
        st.rerun()

    # Reload agent (reset agent without clearing chat)
    if st.button("Reload Agent", width='stretch', help="Reset agent to apply prompt changes"):
        st.session_state.agent = initialize_agent()  # Create fresh agent
        st.rerun()

    st.metric("Messages",         len(st.session_state.messages))
    st.metric("Images Generated", len(st.session_state.generated_images))
    st.metric("PDFs Generated",   len(st.session_state.generated_pdfs))

    st.divider()

    st.subheader("Model Info")
    st.text("Chat:   Claude Sonnet 4")
    st.text("Image:  SD 3.5 Large")
    st.text("Region: us-east-1 / us-west-2")

    st.divider()

    st.subheader("Available Tools")
    st.text("Sales Data Analytics")
    st.text("PDF Report Generation")
    st.text("Chart Rendering")
    st.text("Image Generation")
    st.text("Calculator")
    st.text("Current Time")

    st.divider()

    with st.expander("Sales Data Info"):
        st.markdown("""
        **Dataset:** 2023 & 2024 monthly sales
        **Regions:** North, South
        **Categories:** Electronics, Accessories
        **Metrics:** Revenue, Units, Returns,
        Gross Profit, Margin, Net Revenue
        """)

    st.divider()

    with st.expander("Debug"):
        if hasattr(agent, "tool_names"):
            st.write("Agent tools:", agent.tool_names)

    st.divider()

    with st.expander("Example Prompts"):
        st.markdown("""
        **Sales queries:**
        - Show me monthly sales for 2024
        - Compare 2023 vs 2024 revenue
        - What was the best month in 2023?
        - Show Electronics sales in the North for 2024
        - Why did sales dip in mid-2024?
        - Break down June 2024 by region

        **PDF reports:**
        - Generate a PDF report of 2024 sales
        - Create a PDF with June 2024 breakdown
        - Make a PDF report comparing 2023 vs 2024

        **Other tools:**
        - Generate an image of Tokyo
        - What is 1234 × 5678?
        - What time is it?
        """)