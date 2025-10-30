import streamlit as st
import os
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp import MCPClient
from strands_tools import calculator, current_time

# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="MCP Chat Stream",
    page_icon="🤖",
    layout="wide"
)

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

            # Combine MCP tools with strands_tools
            all_tools = [calculator, current_time] + mcp_tools

            # Create agent with all tools
            agent = Agent(
                tools=all_tools,
                system_prompt="""You are a helpful assistant with access to:
- AWS knowledge and documentation (via MCP)
- Calculator for mathematical operations
- Current time information

Always explain what you're going to do before using tools."""
            )

            # Store in session state
            st.session_state.menu_mcp_chat_stream_agent = agent
            st.session_state.menu_mcp_chat_stream_mcp_client = mcp_client
            st.session_state.menu_mcp_chat_stream_initialized = True
            st.session_state.menu_mcp_chat_stream_tool_count = len(all_tools)

            return True, f"✅ Connected! {len(all_tools)} tools available ({len(mcp_tools)} MCP + 2 built-in)"

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

    st.markdown("---")

    # Available Tools
    st.subheader("🛠️ Available Tools")
    st.text("🧮 Calculator")
    st.text("🕐 Current Time")
    st.text("📚 AWS Knowledge (MCP)")

    st.markdown("---")

    # Chat Controls
    st.subheader("🎛️ Controls")
    if st.button("🗑️ Clear Chat", use_container_width=True, key="menu_mcp_chat_stream_clear"):
        st.session_state.menu_mcp_chat_stream_messages = []
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

        **Time:**
        - What time is it?
        - What's the current date and time?
        """)

# ============================================================
# Main Chat Interface
# ============================================================

st.title("💬 Chat with MCP")
st.caption("Streaming responses with AWS Knowledge, Calculator & Time tools")

# Display chat history
for message in st.session_state.menu_mcp_chat_stream_messages:
    role = message.get("role", "user")
    content = message.get("content", "")
    with st.chat_message(role):
        st.markdown(content)

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
        full_response = ""

        try:
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

            # Add assistant response to history
            st.session_state.menu_mcp_chat_stream_messages.append({
                "role": "assistant",
                "content": full_response
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