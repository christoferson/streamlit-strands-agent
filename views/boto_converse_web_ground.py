import streamlit as st
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import json
from datetime import datetime
import re

# Page configuration
st.set_page_config(
    page_title="Nova Web Grounding Stream",
    page_icon="🌐",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
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

# Check boto3 version (alternative method without pkg_resources)
try:
    boto3_version = boto3.__version__
    botocore_version = boto3.session.Session()._session.user_agent().split()[0].split('/')[-1]
    st.sidebar.caption(f"boto3: {boto3_version}")
except:
    st.sidebar.caption("Version info unavailable")

# Initialize Bedrock client with extended timeout
config = Config(
    read_timeout=900,
    connect_timeout=900,
    retries={'max_attempts': 0}
)

bedrock_client = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-east-1',
    config=config
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "show_citations" not in st.session_state:
    st.session_state.show_citations = True

def sanitize_filename(filename):
    """Sanitize filename to meet Bedrock requirements"""
    name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', ' ', filename)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()
    return name if name else "document"

def format_citations(citations):
    """Format citations for display"""
    if not citations:
        return None

    citation_html = ""
    for idx, citation in enumerate(citations, 1):
        if 'location' in citation and 'web' in citation['location']:
            web = citation['location']['web']
            url = web.get('url', 'Unknown source')
            domain = web.get('domain', '')

            citation_html += f"""
            <div class="citation-box">
                <strong>🔗 Source {idx}:</strong> <a href="{url}" target="_blank">{domain or url}</a>
            </div>
            """
        elif 'title' in citation:
            title = citation.get('title', f'Citation {idx}')
            source_content = citation.get('sourceContent', [])

            content_text = ""
            if source_content:
                for content in source_content[:1]:  # Show first content
                    if 'text' in content:
                        text = content['text']
                        content_text = f"<br><em>{text[:200]}{'...' if len(text) > 200 else ''}</em>"

            citation_html += f"""
            <div class="citation-box">
                <strong>📝 {title}</strong>{content_text}
            </div>
            """

    return citation_html if citation_html else None

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Model Configuration
    st.subheader("Model Settings")
    model_options = {
        "Nova Premier": "us.amazon.nova-premier-v1:0",
    }

    selected_model = st.selectbox(
        "Select Model",
        options=list(model_options.keys()),
        index=0
    )
    model_id = model_options[selected_model]

    # Web Grounding Configuration
    st.subheader("🌐 Web Grounding")
    enable_web_grounding = st.checkbox(
        "Enable Web Grounding",
        value=True,
        help="Allow the model to search for real-time information from the web"
    )

    if enable_web_grounding:
        st.info("✅ Model can access current web information")
        st.caption("Requires latest boto3/botocore")
    else:
        st.warning("⚠️ Model will use only its training data")

    # Inference Parameters
    st.subheader("Inference Parameters")
    max_tokens = st.slider("Max Tokens", 1024, 8192, 4096)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    top_p = st.slider("Top P", 0.0, 1.0, 0.9, 0.1)

    # Display Options
    st.subheader("Display Options")
    st.session_state.show_citations = st.checkbox(
        "Show Citations",
        value=True,
        help="Display source citations and references"
    )

    show_metadata = st.checkbox(
        "Show Metadata",
        value=True,
        help="Display token usage and performance metrics"
    )

    show_grounding_events = st.checkbox(
        "Show Grounding Events",
        value=True,
        help="Display when the model searches for information"
    )

    # System Prompt
    st.subheader("System Prompt")
    system_prompt = st.text_area(
        "System Prompt (Optional)",
        value="You are a helpful AI assistant with access to current information. When answering questions, cite your sources when using web-grounded information.",
        height=120
    )

    # File Upload
    st.subheader("File Upload (Optional)")
    uploaded_file = st.file_uploader(
        "Upload a file",
        type=['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'csv', 'doc', 'docx', 'txt', 'md'],
        help="Upload an image or document to include in your message"
    )

    if uploaded_file:
        file_type = uploaded_file.type
        if file_type.startswith('image/'):
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
        else:
            st.info(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)")

    # Example Questions
    st.subheader("💡 Example Questions")
    if st.button("🌍 Current AWS Regions", use_container_width=True):
        st.session_state.example_question = "What are the current AWS regions and their locations?"

    if st.button("📰 Latest AI News", use_container_width=True):
        st.session_state.example_question = "What are the latest developments in generative AI this week?"

    if st.button("📊 Tech Trends 2024", use_container_width=True):
        st.session_state.example_question = "What are the major technology trends in 2024?"

    if st.button("🚀 Recent Space News", use_container_width=True):
        st.session_state.example_question = "What are the recent developments in space exploration?"

    # Clear conversation button
    st.divider()
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        if 'example_question' in st.session_state:
            del st.session_state.example_question
        st.rerun()

    st.divider()
    st.success("🟢 Connected to Bedrock (us-east-1)")

    if enable_web_grounding:
        st.info("🌐 Web Grounding Active")

# Main content
st.title("🌐 Amazon Nova Web Grounding Stream")
st.markdown("Chat with Amazon Nova Premier with real-time web information access")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display image if present
        if "image" in message:
            st.image(message["image"]["data"], caption="Uploaded Image", width=300)

        # Display document info if present
        if "document" in message:
            st.info(f"📄 {message['document']['original_name']}")

        # Display grounding indicator for user messages
        if message["role"] == "user" and message.get("grounding_enabled"):
            st.markdown("""
            <div class="grounding-indicator">
                🌐 Web Grounding Enabled - Model can search for current information
            </div>
            """, unsafe_allow_html=True)

        # Display text content
        if "text" in message:
            st.markdown(message["text"])

        # Display grounding events
        if "grounding_events" in message and show_grounding_events:
            for event in message["grounding_events"]:
                st.markdown(f"""
                <div class="grounding-indicator">
                    🔍 {event}
                </div>
                """, unsafe_allow_html=True)

        # Display citations
        if "citations" in message and st.session_state.show_citations:
            citation_html = format_citations(message["citations"])
            if citation_html:
                with st.expander("📚 View Sources & Citations", expanded=False):
                    st.markdown(citation_html, unsafe_allow_html=True)

        # Display metadata
        if "metadata" in message and show_metadata:
            metadata = message["metadata"]
            meta_parts = []

            if "usage" in metadata:
                usage = metadata["usage"]
                input_tok = usage.get('inputTokens', 0)
                output_tok = usage.get('outputTokens', 0)
                meta_parts.append(f"Input: {input_tok:,} | Output: {output_tok:,}")

            if "metrics" in metadata:
                metrics = metadata["metrics"]
                latency = metrics.get('latencyMs', 0)
                if latency > 0:
                    meta_parts.append(f"⏱️ {latency:,}ms")

            if meta_parts:
                st.caption(f"📊 {' | '.join(meta_parts)}")

# Get prompt from example or input
default_prompt = st.session_state.pop('example_question', '')

# Chat input
if prompt := st.chat_input("Ask a question...", key="chat_input"):
    user_prompt = prompt
elif default_prompt:
    user_prompt = default_prompt
else:
    user_prompt = None

if user_prompt:
    # Prepare message content for API
    message_content = []
    file_data = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        file_extension = uploaded_file.name.split('.')[-1].lower()
        file_type = uploaded_file.type
        original_filename = uploaded_file.name
        sanitized_filename = sanitize_filename(original_filename)

        # Check if it's an image
        if file_type.startswith('image/'):
            format_mapping = {
                'jpg': 'jpeg',
                'jpeg': 'jpeg',
                'png': 'png',
                'gif': 'gif',
                'webp': 'webp'
            }
            image_format = format_mapping.get(file_extension, 'jpeg')

            message_content.append({
                "image": {
                    "format": image_format,
                    "source": {"bytes": file_bytes}
                }
            })

            file_data = {
                "type": "image",
                "data": file_bytes,
                "format": image_format,
                "original_name": original_filename
            }
        else:
            doc_format_mapping = {
                'pdf': 'pdf', 'csv': 'csv', 'doc': 'doc',
                'docx': 'docx', 'txt': 'txt', 'md': 'md'
            }
            doc_format = doc_format_mapping.get(file_extension, 'txt')

            message_content.append({
                "document": {
                    "format": doc_format,
                    "name": sanitized_filename,
                    "source": {"bytes": file_bytes}
                }
            })

            file_data = {
                "type": "document",
                "name": sanitized_filename,
                "original_name": original_filename,
                "format": doc_format,
                "content": file_bytes
            }

    # Add text to message content
    message_content.append({"text": user_prompt})

    # Add user message to chat history
    user_message = {
        "role": "user",
        "text": user_prompt,
        "grounding_enabled": enable_web_grounding
    }

    if file_data:
        if file_data["type"] == "image":
            user_message["image"] = {
                "data": file_data["data"],
                "format": file_data["format"],
                "original_name": file_data["original_name"]
            }
        elif file_data["type"] == "document":
            user_message["document"] = {
                "name": file_data["name"],
                "original_name": file_data["original_name"],
                "format": file_data["format"],
                "content": file_data["content"]
            }

    st.session_state.messages.append(user_message)

    # Display user message
    with st.chat_message("user"):
        if file_data:
            if file_data["type"] == "image":
                st.image(file_data["data"], caption="Uploaded Image", width=300)
            elif file_data["type"] == "document":
                st.info(f"📄 {file_data['original_name']}")

        if enable_web_grounding:
            st.markdown("""
            <div class="grounding-indicator">
                🌐 Web Grounding Enabled - Model can search for current information
            </div>
            """, unsafe_allow_html=True)

        st.markdown(user_prompt)

    # Display assistant response with streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        grounding_placeholder = st.empty()
        citation_placeholder = st.empty()
        metadata_placeholder = st.empty()

        full_response = ""
        grounding_events = []
        citations = []
        metadata = {"usage": {}, "metrics": {}}

        try:
            # Prepare messages for API
            api_messages = []
            for msg in st.session_state.messages:
                content = []

                if "image" in msg:
                    content.append({
                        "image": {
                            "format": msg["image"]["format"],
                            "source": {"bytes": msg["image"]["data"]}
                        }
                    })

                if "document" in msg:
                    doc = msg["document"]
                    content.append({
                        "document": {
                            "format": doc["format"],
                            "name": doc["name"],
                            "source": {"bytes": doc["content"]}
                        }
                    })

                if "text" in msg:
                    content.append({"text": msg["text"]})

                api_messages.append({
                    "role": msg["role"],
                    "content": content
                })

            # Prepare system prompt
            system_config = None
            if system_prompt.strip():
                system_config = [{"text": system_prompt}]

            # Prepare tool configuration for Web Grounding
            tool_config = None
            if enable_web_grounding:
                tool_config = {
                    "tools": [
                        {
                            "systemTool": {
                                "name": "nova_grounding"
                            }
                        }
                    ]
                }

            # Call converse_stream API
            api_params = {
                "modelId": model_id,
                "messages": api_messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                }
            }

            if system_config:
                api_params["system"] = system_config

            if tool_config:
                api_params["toolConfig"] = tool_config

            response = bedrock_client.converse_stream(**api_params)

            # Process the stream
            stream = response.get('stream')
            if stream:
                for event in stream:
                    # Handle content block start
                    if 'contentBlockStart' in event:
                        block_start = event['contentBlockStart']
                        if 'start' in block_start:
                            start_data = block_start['start']
                            if 'toolUse' in start_data:
                                tool_use = start_data['toolUse']
                                tool_name = tool_use.get('name', 'unknown')
                                grounding_events.append(f"🔍 Searching web using {tool_name}...")
                                if show_grounding_events:
                                    grounding_placeholder.markdown(
                                        f'<div class="grounding-indicator">{grounding_events[-1]}</div>',
                                        unsafe_allow_html=True
                                    )

                    # Handle content block delta (streaming text)
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']['delta']
                        if 'text' in delta:
                            text_chunk = delta['text']
                            full_response += text_chunk
                            message_placeholder.markdown(full_response + "▌")

                        # Handle citation deltas
                        if 'citation' in delta:
                            citations.append(delta['citation'])

                    # Handle content block stop
                    if 'contentBlockStop' in event:
                        if grounding_events and show_grounding_events:
                            grounding_events.append("✅ Web search completed")
                            grounding_placeholder.markdown(
                                '<br>'.join([f'<div class="grounding-indicator">{e}</div>' 
                                           for e in grounding_events]),
                                unsafe_allow_html=True
                            )

                    # Handle message stop
                    elif 'messageStop' in event:
                        stop_reason = event['messageStop'].get('stopReason', 'unknown')
                        if stop_reason != 'end_turn':
                            st.info(f"ℹ️ Stop reason: {stop_reason}")

                    # Handle metadata
                    elif 'metadata' in event:
                        event_metadata = event['metadata']

                        if 'usage' in event_metadata:
                            metadata['usage'] = event_metadata['usage']

                        if 'metrics' in event_metadata:
                            metadata['metrics'] = event_metadata['metrics']

            # Update the final message
            message_placeholder.markdown(full_response)

            # Display citations
            if citations and st.session_state.show_citations:
                citation_html = format_citations(citations)
                if citation_html:
                    with citation_placeholder.expander("📚 View Sources & Citations", expanded=True):
                        st.markdown(citation_html, unsafe_allow_html=True)

            # Display metadata
            if show_metadata:
                meta_parts = []

                if metadata.get('usage'):
                    usage = metadata['usage']
                    input_tok = usage.get('inputTokens', 0)
                    output_tok = usage.get('outputTokens', 0)
                    meta_parts.append(f"Input: {input_tok:,} | Output: {output_tok:,}")

                if metadata.get('metrics'):
                    metrics = metadata['metrics']
                    latency = metrics.get('latencyMs', 0)
                    if latency > 0:
                        meta_parts.append(f"⏱️ {latency:,}ms")

                if meta_parts:
                    metadata_placeholder.caption(f"📊 {' | '.join(meta_parts)}")

            # Add assistant response to chat history
            assistant_message = {
                "role": "assistant",
                "text": full_response,
                "metadata": metadata
            }

            if grounding_events:
                assistant_message["grounding_events"] = grounding_events

            if citations:
                assistant_message["citations"] = citations

            st.session_state.messages.append(assistant_message)

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            st.error(f"❌ AWS Error ({error_code}): {error_message}")

            if "systemTool" in error_message or "toolConfig" in error_message:
                st.error("""
                **Web Grounding Not Supported**

                Your boto3/botocore version may not support Web Grounding yet.

                Please upgrade:
                ```bash
                pip install --upgrade boto3 botocore
                ```

                Required versions:
                - boto3 >= 1.35.0
                - botocore >= 1.35.0
                """)

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Show full traceback"):
                st.code(traceback.format_exc())

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Messages", len(st.session_state.messages))
with col2:
    user_msgs = len([m for m in st.session_state.messages if m["role"] == "user"])
    st.metric("User Messages", user_msgs)
with col3:
    assistant_msgs = len([m for m in st.session_state.messages if m["role"] == "assistant"])
    st.metric("Assistant Messages", assistant_msgs)

st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p>Built with Streamlit and Amazon Bedrock Nova | 
    <a href='https://aws.amazon.com/bedrock/nova/' target='_blank'>Learn more about Amazon Nova</a></p>
</div>
""", unsafe_allow_html=True)