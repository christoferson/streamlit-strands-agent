import streamlit as st
from strands import Agent, tool
from strands.models import BedrockModel
from strands_tools import calculator, current_time
import boto3
import json
import base64
from io import BytesIO
from PIL import Image
import random
import asyncio
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Strands Web Grounding Chat",
    page_icon="🌐",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .citation-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #ff9900;
        font-size: 0.9em;
    }
    .grounding-indicator {
        background-color: #e8f4f8;
        padding: 0.5rem;
        border-radius: 0.3rem;
        margin: 0.5rem 0;
        border-left: 3px solid #0073bb;
        font-size: 0.85em;
    }
    </style>
""", unsafe_allow_html=True)

# Create bedrock clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
bedrock_runtime_grounding = boto3.client('bedrock-runtime', region_name='us-east-1')

# Check boto3 version for Web Grounding support
try:
    boto3_version = boto3.__version__
    version_parts = boto3_version.split('.')
    major = int(version_parts[0])
    minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    web_grounding_supported = (major > 1) or (major == 1 and minor >= 35)
except:
    web_grounding_supported = False

@tool
async def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """
    Generate an image using Stability AI based on a text description.

    Use this tool when users ask you to create, generate, draw, make, or produce images.

    Args:
        prompt: Detailed text description of the image to generate
        aspect_ratio: Image aspect ratio (1:1, 16:9, 9:16, etc.)

    Returns:
        str: Success message with generation details
    """
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
            lambda: bedrock_runtime.invoke_model(
                modelId="stability.sd3-5-large-v1:0",
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request)
            )
        )

        response_body = json.loads(response.get("body").read())
        finish_reason = response_body.get("finish_reasons", [None])[0]

        if finish_reason is not None:
            return f"Image generation error: {finish_reason}"

        response_image_base64 = response_body["images"][0]
        image_bytes = base64.b64decode(response_image_base64)

        if 'generated_images' not in st.session_state:
            st.session_state.generated_images = []

        st.session_state.generated_images.append(image_bytes)

        return f"✅ Image generated successfully! (seed: {seed})"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error: {str(e)}\n{error_details}"

@tool
async def search_web(query: str) -> str:
    """
    Search the web for current, real-time information using Amazon Nova's Web Grounding.

    Use this tool when users ask about:
    - Current events, news, or recent developments
    - Latest information that may have changed recently
    - Real-time data like AWS regions, service updates, or announcements
    - Any information that requires up-to-date sources

    Args:
        query: The search query or question to find current information about

    Returns:
        str: Current information with source citations
    """
    if not web_grounding_supported:
        return "❌ Web Grounding requires boto3 >= 1.35.36. Please upgrade: pip install --upgrade boto3 botocore"

    try:
        # Prepare the request with Web Grounding
        request = {
            "modelId": "us.amazon.nova-premier-v1:0",
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": query}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 2048,
                "temperature": 0.7,
                "topP": 0.9
            },
            "toolConfig": {
                "tools": [
                    {
                        "systemTool": {
                            "name": "nova_grounding"
                        }
                    }
                ]
            }
        }

        # Store grounding event
        if 'grounding_events' not in st.session_state:
            st.session_state.grounding_events = []

        st.session_state.grounding_events.append({
            "query": query,
            "timestamp": datetime.now().isoformat()
        })

        # Make the API call
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: bedrock_runtime_grounding.converse(**request)
        )

        # Extract response text
        output_message = response.get('output', {}).get('message', {})
        content_blocks = output_message.get('content', [])

        response_text = ""
        citations = []

        for block in content_blocks:
            if 'text' in block:
                response_text += block['text']

            # Extract citations if available
            if 'citationsContent' in block:
                citations_content = block['citationsContent']
                if 'citations' in citations_content:
                    citations.extend(citations_content['citations'])

        # Store citations in session state
        if citations:
            if 'web_citations' not in st.session_state:
                st.session_state.web_citations = []
            st.session_state.web_citations.extend(citations)

        # Format response with citations
        result = f"🌐 **Web Search Results:**\n\n{response_text}"

        if citations:
            result += "\n\n📚 **Sources:**\n"
            for idx, citation in enumerate(citations, 1):
                if 'location' in citation and 'web' in citation['location']:
                    web = citation['location']['web']
                    url = web.get('url', 'Unknown')
                    domain = web.get('domain', '')
                    result += f"\n{idx}. {domain}: {url}"
                elif 'title' in citation:
                    result += f"\n{idx}. {citation['title']}"

        return result

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Web search error: {str(e)}\n{error_details}"

# Initialize agent
@st.cache_resource
def initialize_agent(enable_web_grounding: bool):
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        temperature=0.1,
    )

    tools_list = [calculator, current_time, generate_image]

    if enable_web_grounding and web_grounding_supported:
        tools_list.append(search_web)

    system_prompt = """You are a helpful assistant with access to multiple tools.

IMPORTANT: Before using any tool, always explain what you're going to do first.

**Tool Usage Guidelines:**

1. **search_web** - Use when users ask about:
   - Current events, news, or recent information
   - Latest updates, announcements, or changes
   - Real-time data (AWS regions, service updates, etc.)
   - Any information that requires up-to-date sources
   - Example: "Let me search for the latest information about..."

2. **calculator** - Use for mathematical calculations
   - Example: "I'll calculate that for you..."

3. **current_time** - Use to get the current date/time
   - Example: "Let me check the current time..."

4. **generate_image** - Use to create images from descriptions
   - Example: "I'll generate an image of [description]..."

Always provide context before and after using tools. When using search_web, summarize the findings and cite sources."""

    agent = Agent(
        model=bedrock_model,
        system_prompt=system_prompt,
        tools=tools_list
    )

    return agent

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Web Grounding toggle
    st.subheader("🌐 Web Grounding")

    if not web_grounding_supported:
        st.error("❌ Web Grounding Not Available")
        st.caption(f"boto3: {boto3.__version__}")
        st.markdown("""
        **Upgrade Required:**
        ```bash
        pip install --upgrade boto3 botocore
        ```
        Required: boto3 >= 1.35.36
        """)
        enable_web_grounding = False
    else:
        enable_web_grounding = st.checkbox(
            "Enable Web Grounding",
            value=True,
            help="Allow the agent to search for real-time information"
        )

        if enable_web_grounding:
            st.success("✅ Web search enabled")
        else:
            st.warning("⚠️ Using training data only")

    st.divider()

    # Chat controls
    st.header("Chat Controls")

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.session_state.web_citations = []
        st.session_state.grounding_events = []
        st.cache_resource.clear()
        st.rerun()

    # Metrics
    st.metric("Messages", len(st.session_state.get('messages', [])))
    st.metric("Images Generated", len(st.session_state.get('generated_images', [])))
    st.metric("Web Searches", len(st.session_state.get('grounding_events', [])))

    st.divider()

    # Model info
    st.subheader("Model Info")
    st.text("Chat: Claude Sonnet 4")
    st.text("Web: Nova Premier")
    st.text("Image: SD 3.5 Large")
    st.caption(f"boto3: {boto3.__version__}")

    st.divider()

    # Available tools
    st.subheader("Available Tools")
    if enable_web_grounding and web_grounding_supported:
        st.text("🌐 Web Search")
    st.text("🎨 Image Generation")
    st.text("🧮 Calculator")
    st.text("🕐 Current Time")

    st.divider()

    # Example prompts
    with st.expander("💡 Example Prompts"):
        st.markdown("""
        **Web Grounding:**
        - What are the current AWS regions?
        - Latest AI news this week
        - Recent Amazon Bedrock updates

        **Image Generation:**
        - Generate an image of Tokyo at night
        - Create a futuristic cityscape

        **Calculations:**
        - What is 1234 * 5678?
        - Calculate 15% of 2500

        **Time:**
        - What time is it?
        - What's today's date?
        """)

    st.divider()

    # Citations viewer
    if st.session_state.get('web_citations'):
        with st.expander("📚 View All Citations"):
            for idx, citation in enumerate(st.session_state.web_citations, 1):
                if 'location' in citation and 'web' in citation['location']:
                    web = citation['location']['web']
                    url = web.get('url', 'Unknown')
                    domain = web.get('domain', '')
                    st.markdown(f"**{idx}.** [{domain}]({url})")
                elif 'title' in citation:
                    st.markdown(f"**{idx}.** {citation['title']}")

# Initialize agent with current settings
agent = initialize_agent(enable_web_grounding)

# Main content
st.title("🌐 Strands Web Grounding Chat")
st.caption("Powered by Claude Sonnet 4, Nova Premier & Stability AI")

# Show Web Grounding status
if enable_web_grounding and web_grounding_supported:
    st.info("🌐 Web Grounding Active - Agent can search for current information")
elif not web_grounding_supported:
    st.warning("⚠️ Web Grounding unavailable - Upgrade boto3 to enable")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

if "web_citations" not in st.session_state:
    st.session_state.web_citations = []

if "grounding_events" not in st.session_state:
    st.session_state.grounding_events = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            if message.get("text"):
                st.markdown(message.get("text"))
            st.image(message["content"], use_column_width=True)
        elif message.get("type") == "web_search":
            st.markdown(message["content"])
            # Show grounding indicator
            if message.get("grounding_used"):
                st.markdown("""
                <div class="grounding-indicator">
                    🔍 Used web search for current information
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask me anything..."):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            # Track initial counts
            images_before = len(st.session_state.generated_images)
            citations_before = len(st.session_state.web_citations)
            grounding_before = len(st.session_state.grounding_events)

            # Stream the response
            async def stream_response():
                response_text = ""
                async for chunk in agent.stream_async(prompt):
                    if isinstance(chunk, str):
                        response_text += chunk
                        message_placeholder.markdown(response_text + "▌")
                    elif isinstance(chunk, dict):
                        if 'event' in chunk:
                            event = chunk['event']

                            if 'contentBlockDelta' in event:
                                delta = event['contentBlockDelta'].get('delta', {})
                                if 'text' in delta:
                                    response_text += delta['text']
                                    message_placeholder.markdown(response_text + "▌")

                            elif 'text' in event:
                                response_text += event['text']
                                message_placeholder.markdown(response_text + "▌")

                message_placeholder.markdown(response_text)
                return response_text

            # Run streaming
            full_response = asyncio.run(stream_response())

            # Check what was generated/searched
            images_after = len(st.session_state.generated_images)
            citations_after = len(st.session_state.web_citations)
            grounding_after = len(st.session_state.grounding_events)

            grounding_used = grounding_after > grounding_before

            # Display new images
            if images_after > images_before:
                for i in range(images_before, images_after):
                    image_bytes = st.session_state.generated_images[i]
                    image = Image.open(BytesIO(image_bytes))
                    st.image(image, use_column_width=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "image",
                    "text": full_response,
                    "content": image
                })
            else:
                # Text response (possibly with web grounding)
                st.session_state.messages.append({
                    "role": "assistant",
                    "type": "web_search" if grounding_used else "text",
                    "content": full_response,
                    "grounding_used": grounding_used
                })

            # Show grounding indicator if used
            if grounding_used:
                st.markdown("""
                <div class="grounding-indicator">
                    🔍 Used web search for current information
                </div>
                """, unsafe_allow_html=True)

            # Display new citations
            if citations_after > citations_before:
                with st.expander("📚 View Sources", expanded=True):
                    for i in range(citations_before, citations_after):
                        citation = st.session_state.web_citations[i]
                        if 'location' in citation and 'web' in citation['location']:
                            web = citation['location']['web']
                            url = web.get('url', 'Unknown')
                            domain = web.get('domain', '')
                            st.markdown(f"""
                            <div class="citation-box">
                                <strong>🔗 Source:</strong> <a href="{url}" target="_blank">{domain}</a>
                            </div>
                            """, unsafe_allow_html=True)

        except Exception as e:
            error_message = f"Error: {str(e)}"
            st.error(error_message)
            import traceback
            st.code(traceback.format_exc())
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_message
            })

# Footer
st.divider()
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Messages", len(st.session_state.messages))
with col2:
    st.metric("Images", len(st.session_state.generated_images))
with col3:
    st.metric("Web Searches", len(st.session_state.grounding_events))
with col4:
    st.metric("Citations", len(st.session_state.web_citations))