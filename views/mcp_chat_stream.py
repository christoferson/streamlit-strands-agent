import streamlit as st
import os
import asyncio
import json
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent, tool
from strands.tools.mcp import MCPClient
from strands_tools import calculator, current_time
import plotly.graph_objects as go
import plotly.express as px

# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="MCP Chat Stream",
    page_icon="🤖",
    layout="wide"
)

# ============================================================
# Custom Plotly Chart Tool
# ============================================================

@tool
async def create_bar_chart(
    data: str,
    title: str = "Bar Chart",
    x_label: str = "X Axis",
    y_label: str = "Y Axis",
    colors: str = None
) -> str:
    """
    Create an interactive colored bar chart using Plotly.

    Args:
        data: JSON string with format: {"labels": ["2018", "2019"], "values": [548.9, 556.0]}
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colors: Optional JSON array of colors like ["blue", "green", "red"] or single color

    Returns:
        Success message with chart stored in session state

    Example:
        data='{"labels": ["2018", "2019", "2020"], "values": [548.9, 556.0, 539.2]}'
        colors='["blue", "blue", "red"]'
    """
    try:
        # Parse data
        chart_data = json.loads(data)
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])

        if not labels or not values:
            return "❌ Error: Data must contain 'labels' and 'values' arrays"

        if len(labels) != len(values):
            return "❌ Error: Labels and values must have the same length"

        # Parse colors if provided
        color_list = None
        if colors:
            try:
                color_list = json.loads(colors)
            except:
                # If not JSON, treat as single color
                color_list = colors

        # Create figure
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=values,
                marker_color=color_list,
                text=[f"{v:,.1f}" for v in values],
                textposition='outside',
                textfont=dict(size=12),
            )
        ])

        # Update layout
        fig.update_layout(
            title=dict(text=title, font=dict(size=20)),
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_white",
            height=500,
            showlegend=False,
            hovermode='x unified'
        )

        # Store in session state
        if 'menu_mcp_chat_stream_charts' not in st.session_state:
            st.session_state.menu_mcp_chat_stream_charts = []

        st.session_state.menu_mcp_chat_stream_charts.append(fig)

        return f"✅ Bar chart '{title}' created successfully with {len(labels)} bars!"

    except json.JSONDecodeError as e:
        return f"❌ Error parsing JSON data: {str(e)}"
    except Exception as e:
        return f"❌ Error creating chart: {str(e)}"


@tool
async def create_line_chart(
    data: str,
    title: str = "Line Chart",
    x_label: str = "X Axis",
    y_label: str = "Y Axis",
    color: str = "blue"
) -> str:
    """
    Create an interactive line chart using Plotly.

    Args:
        data: JSON string with format: {"labels": ["2018", "2019"], "values": [548.9, 556.0]}
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        color: Line color (default: blue)

    Returns:
        Success message with chart stored in session state
    """
    try:
        # Parse data
        chart_data = json.loads(data)
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])

        if not labels or not values:
            return "❌ Error: Data must contain 'labels' and 'values' arrays"

        # Create figure
        fig = go.Figure(data=[
            go.Scatter(
                x=labels,
                y=values,
                mode='lines+markers',
                line=dict(color=color, width=3),
                marker=dict(size=8),
                text=[f"{v:,.1f}" for v in values],
                hovertemplate='%{x}<br>%{y:,.1f}<extra></extra>'
            )
        ])

        # Update layout
        fig.update_layout(
            title=dict(text=title, font=dict(size=20)),
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="plotly_white",
            height=500,
            hovermode='x unified'
        )

        # Store in session state
        if 'menu_mcp_chat_stream_charts' not in st.session_state:
            st.session_state.menu_mcp_chat_stream_charts = []

        st.session_state.menu_mcp_chat_stream_charts.append(fig)

        return f"✅ Line chart '{title}' created successfully with {len(labels)} data points!"

    except Exception as e:
        return f"❌ Error creating chart: {str(e)}"

# ============================================================
# Session State Initialization
# ============================================================

def init_session_state():
    """Initialize all session state variables with prefix to avoid clashes"""
    if "menu_mcp_chat_stream_messages" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_messages = []

    if "menu_mcp_chat_stream_agent" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_agent = None

    if "menu_mcp_chat_stream_initialized" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_initialized = False

    if "menu_mcp_chat_stream_mcp_client" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_mcp_client = None

    if "menu_mcp_chat_stream_tool_count" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_tool_count = 0

    if "menu_mcp_chat_stream_charts" not in st.session_state:
        st.session_state.menu_mcp_chat_stream_charts = []

# ============================================================
# MCP Connection & Agent Initialization
# ============================================================

def connect_to_mcp(mcp_url: str):
    """
    Connect to MCP server and initialize agent with tools

    Args:
        mcp_url: URL of the MCP server to connect to

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Create MCP client
        mcp_client = MCPClient(
            transport_callable=lambda: streamablehttp_client(url=mcp_url)
        )

        # Get tools from MCP server
        with mcp_client as client:
            mcp_tools = client.list_tools_sync()

            # Combine MCP tools with strands_tools and custom plotly tools
            all_tools = [
                calculator, 
                current_time, 
                create_bar_chart, 
                create_line_chart
            ] + mcp_tools

            # Create agent with all tools
            agent = Agent(
                tools=all_tools,
                system_prompt="""You are a helpful assistant with access to:
- AWS knowledge and documentation (via MCP)
- Calculator for mathematical operations
- Current time information
- Interactive chart creation (bar charts and line charts)

When creating charts:
1. Always format data as JSON with "labels" and "values" arrays
2. Use descriptive titles and axis labels
3. For bar charts, you can specify colors as JSON array or single color
4. Always explain what you're going to do before using tools

Example chart data format:
{"labels": ["2018", "2019", "2020"], "values": [548.9, 556.0, 539.2]}

Example colors format:
["blue", "green", "red"] or just "blue" for all bars"""
            )

            # Store in session state
            st.session_state.menu_mcp_chat_stream_agent = agent
            st.session_state.menu_mcp_chat_stream_mcp_client = mcp_client
            st.session_state.menu_mcp_chat_stream_initialized = True
            st.session_state.menu_mcp_chat_stream_tool_count = len(all_tools)

            return True, f"✅ Connected! {len(all_tools)} tools available ({len(mcp_tools)} MCP + 4 built-in)"

    except Exception as e:
        return False, f"❌ Connection Error: {str(e)}"

# ============================================================
# Auto-Connect on First Load
# ============================================================

init_session_state()

if not st.session_state.menu_mcp_chat_stream_initialized:
    default_mcp_url = "https://knowledge-mcp.global.api.aws"
    with st.spinner("🔄 Connecting to MCP server..."):
        success, message = connect_to_mcp(default_mcp_url)
        if success:
            st.success(message)
        else:
            st.error(message)

# ============================================================
# Sidebar - Controls & Configuration
# ============================================================

with st.sidebar:
    st.title("🤖 MCP Chat Stream")
    st.markdown("---")

    # MCP Server Configuration
    st.subheader("📡 MCP Server")
    mcp_url = st.text_input(
        "Server URL",
        value="https://knowledge-mcp.global.api.aws",
        key="menu_mcp_chat_stream_url"
    )

    if st.button("🔄 Reconnect", use_container_width=True, key="menu_mcp_chat_stream_reconnect"):
        with st.spinner("Connecting..."):
            success, message = connect_to_mcp(mcp_url)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    # Connection Status
    if st.session_state.menu_mcp_chat_stream_initialized:
        st.success("✅ Connected")
    else:
        st.warning("⚠️ Not Connected")

    st.markdown("---")

    # Statistics
    st.subheader("📊 Statistics")
    st.metric("Tools Available", st.session_state.menu_mcp_chat_stream_tool_count)
    st.metric("Messages", len(st.session_state.menu_mcp_chat_stream_messages))
    st.metric("Charts Created", len(st.session_state.menu_mcp_chat_stream_charts))

    st.markdown("---")

    # Available Tools
    st.subheader("🛠️ Available Tools")
    st.text("🧮 Calculator")
    st.text("🕐 Current Time")
    st.text("📊 Bar Chart")
    st.text("📈 Line Chart")
    st.text("📚 AWS Knowledge (MCP)")

    st.markdown("---")

    # Chat Controls
    st.subheader("🎛️ Controls")
    if st.button("🗑️ Clear Chat", use_container_width=True, key="menu_mcp_chat_stream_clear"):
        st.session_state.menu_mcp_chat_stream_messages = []
        st.session_state.menu_mcp_chat_stream_charts = []
        st.rerun()

    st.markdown("---")

    # Example Queries
    with st.expander("💡 Example Queries"):
        st.markdown("""
        **AWS Questions:**
        - What are AWS S3 bucket naming rules?
        - Is Lambda available in eu-west-1?
        - Explain DynamoDB best practices

        **Calculator:**
        - What is 1234 * 5678?
        - Calculate 15% of 250

        **Charts:**
        - Create a bar chart of Japan's GDP from 2018 to 2023
        - Show me a line chart of quarterly sales
        - Make a colored bar chart comparing AWS regions

        **Time:**
        - What time is it?
        - What's the current date and time?
        """)

# ============================================================
# Main Chat Interface
# ============================================================

st.title("💬 Chat with MCP")
st.caption("Streaming responses with AWS Knowledge, Calculator, Time & Chart tools")

# Display chat history
for message in st.session_state.menu_mcp_chat_stream_messages:
    role = message.get("role", "user")
    content = message.get("content", "")
    chart_index = message.get("chart_index", None)

    with st.chat_message(role):
        st.markdown(content)

        # Display chart if this message has one
        if chart_index is not None and chart_index < len(st.session_state.menu_mcp_chat_stream_charts):
            st.plotly_chart(
                st.session_state.menu_mcp_chat_stream_charts[chart_index],
                use_container_width=True,
                key=f"chart_history_{chart_index}"
            )

# ============================================================
# Chat Input & Response Streaming
# ============================================================

if prompt := st.chat_input(
    "Ask a question...",
    disabled=not st.session_state.menu_mcp_chat_stream_initialized,
    key="menu_mcp_chat_stream_input"
):
    # Add user message to history
    st.session_state.menu_mcp_chat_stream_messages.append({
        "role": "user",
        "content": prompt
    })

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and stream assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        chart_placeholder = st.empty()
        full_response = ""

        try:
            # Track charts before response
            charts_before = len(st.session_state.menu_mcp_chat_stream_charts)

            # Stream the response
            async def stream_response():
                """Stream response from agent asynchronously"""
                response_text = ""

                # Use MCP client context
                with st.session_state.menu_mcp_chat_stream_mcp_client:
                    async for chunk in st.session_state.menu_mcp_chat_stream_agent.stream_async(prompt):
                        # Handle text chunks
                        if isinstance(chunk, str):
                            response_text += chunk
                            message_placeholder.markdown(response_text + "▌")

                        # Handle event-based chunks
                        elif isinstance(chunk, dict):
                            if 'event' in chunk:
                                event = chunk['event']

                                # Handle text deltas
                                if 'contentBlockDelta' in event:
                                    delta = event['contentBlockDelta'].get('delta', {})
                                    if 'text' in delta:
                                        response_text += delta['text']
                                        message_placeholder.markdown(response_text + "▌")

                                # Handle complete text
                                elif 'text' in event:
                                    response_text += event['text']
                                    message_placeholder.markdown(response_text + "▌")

                # Remove cursor
                message_placeholder.markdown(response_text)
                return response_text

            # Run streaming
            full_response = asyncio.run(stream_response())

            # Check if new charts were created
            charts_after = len(st.session_state.menu_mcp_chat_stream_charts)
            chart_index = None

            if charts_after > charts_before:
                # Display the new chart
                chart_index = charts_after - 1
                chart_placeholder.plotly_chart(
                    st.session_state.menu_mcp_chat_stream_charts[chart_index],
                    use_container_width=True,
                    key=f"chart_new_{chart_index}"
                )

            # Add assistant response to history
            st.session_state.menu_mcp_chat_stream_messages.append({
                "role": "assistant",
                "content": full_response,
                "chart_index": chart_index
            })

        except Exception as e:
            error_message = f"❌ Error: {str(e)}"
            st.error(error_message)

            # Add error to history
            st.session_state.menu_mcp_chat_stream_messages.append({
                "role": "assistant",
                "content": error_message
            })

            # Show traceback in expander
            with st.expander("🔍 Error Details"):
                import traceback
                st.code(traceback.format_exc())

# ============================================================
# Connection Status Message
# ============================================================

if not st.session_state.menu_mcp_chat_stream_initialized:
    st.info("⏳ Connecting to MCP server... Please wait.")