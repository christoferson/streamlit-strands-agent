import streamlit as st
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import re

# Page configuration
st.set_page_config(
    page_title="Bedrock Converse Stream",
    page_icon="💬",
    layout="wide"
)

# Initialize Bedrock client with 15-minute timeout
config = Config(
    read_timeout=900,  # 15 minutes
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

def sanitize_filename(filename):
    """
    Sanitize filename to meet Bedrock requirements:
    - Only alphanumeric, whitespace, hyphens, parentheses, square brackets
    - No more than one consecutive whitespace
    """
    # Replace periods and other special chars with spaces
    name = re.sub(r'[^a-zA-Z0-9\s\-\(\)\[\]]', ' ', filename)
    # Replace multiple consecutive spaces with single space
    name = re.sub(r'\s+', ' ', name)
    # Trim whitespace
    name = name.strip()
    return name if name else "document"

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Model Configuration
    st.subheader("Model Settings")
    model_options = {
        "Claude Sonnet 4.5": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "Claude Haiku 4.5": "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    }

    selected_model = st.selectbox(
        "Select Model",
        options=list(model_options.keys()),
        index=0
    )
    model_id = model_options[selected_model]

    # Inference Parameters
    st.subheader("Inference Parameters")
    max_tokens = st.slider("Max Tokens", 4096, 4096*3, 4096)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.1, 0.1)

    # Cache Configuration
    st.subheader("Cache Configuration")
    enable_system_cache = st.checkbox(
        "Cache System Prompt",
        value=False,
        help="Cache the system prompt to reduce latency and costs for repeated requests"
    )

    enable_document_cache = st.checkbox(
        "Cache Documents",
        value=False,
        help="Cache uploaded documents to reduce processing time in multi-turn conversations"
    )

    # System Prompt
    st.subheader("System Prompt")
    system_prompt = st.text_area(
        "System Prompt (Optional)",
        value="You are a helpful AI assistant.",
        height=100
    )

    # File Upload
    st.subheader("File Upload (Optional)")
    uploaded_file = st.file_uploader(
        "Upload a file",
        type=['png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'csv', 'doc', 'docx', 'xls', 'xlsx', 'html', 'txt', 'md'],
        help="Upload an image or document to include in your message"
    )

    if uploaded_file:
        file_type = uploaded_file.type
        if file_type.startswith('image/'):
            st.image(uploaded_file, caption="Uploaded Image", width='stretch')
        else:
            st.info(f"📄 {uploaded_file.name} ({uploaded_file.size} bytes)")

    # Clear conversation button
    if st.button("Clear Conversation"):
        st.session_state.messages = []
        st.rerun()

    st.success("🟢 Connected to Bedrock (us-east-1)")

    # Cache info
    if enable_system_cache or enable_document_cache:
        st.info("💾 Caching enabled - First request writes to cache, subsequent requests read from cache")

# Main content
st.title("💬 AWS Bedrock Converse Stream")
st.markdown("Chat with AWS Bedrock models using the Converse Stream API")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Display image if present
        if "image" in message:
            st.image(message["image"]["data"], caption="Uploaded Image", width=300)

        # Display document info if present
        if "document" in message:
            st.info(f"📄 {message['document']['original_name']}")

        # Display text content
        if "text" in message:
            st.markdown(message["text"])

        # Display metadata if present (for assistant messages)
        if "metadata" in message:
            metadata = message["metadata"]

            # Build metadata string
            meta_parts = []

            # Token usage
            if "usage" in metadata:
                usage = metadata["usage"]
                input_tok = usage.get('inputTokens', 0)
                output_tok = usage.get('outputTokens', 0)
                cache_read = usage.get('cacheReadInputTokens', 0)
                cache_write = usage.get('cacheWriteInputTokens', 0)

                meta_parts.append(f"Input: {input_tok:,} | Output: {output_tok:,}")

                if cache_read > 0:
                    meta_parts.append(f"💾 Cache Read: {cache_read:,}")
                if cache_write > 0:
                    meta_parts.append(f"💾 Cache Write: {cache_write:,}")

            # Latency
            if "metrics" in metadata:
                metrics = metadata["metrics"]
                latency = metrics.get('latencyMs', 0)
                if latency > 0:
                    meta_parts.append(f"⏱️ {latency:,}ms")

            if meta_parts:
                st.caption(f"📊 {' | '.join(meta_parts)}")

# Chat input
if prompt := st.chat_input("Type your message here..."):
    # Prepare message content for API
    message_content = []

    # Store file data for history
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
                    "source": {
                        "bytes": file_bytes
                    }
                }
            })

            file_data = {
                "type": "image",
                "data": file_bytes,
                "format": image_format,
                "original_name": original_filename
            }

        # All documents use bytes (not text field)
        else:
            doc_format_mapping = {
                'pdf': 'pdf',
                'csv': 'csv',
                'doc': 'doc',
                'docx': 'docx',
                'xls': 'xls',
                'xlsx': 'xlsx',
                'html': 'html',
                'txt': 'txt',
                'md': 'md'
            }
            doc_format = doc_format_mapping.get(file_extension, 'txt')

            message_content.append({
                "document": {
                    "format": doc_format,
                    "name": sanitized_filename,
                    "source": {
                        "bytes": file_bytes
                    }
                }
            })

            # Add cache point for document if enabled
            if enable_document_cache:
                message_content.append({
                    "cachePoint": {
                        "type": "default"
                    }
                })

            file_data = {
                "type": "document",
                "name": sanitized_filename,
                "original_name": original_filename,
                "format": doc_format,
                "content": file_bytes,
                "cached": enable_document_cache
            }

    # Add text to message content
    message_content.append({"text": prompt})

    # Add user message to chat history
    user_message = {"role": "user", "text": prompt}
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
                "content": file_data["content"],
                "cached": file_data.get("cached", False)
            }

    st.session_state.messages.append(user_message)

    # Display user message
    with st.chat_message("user"):
        if file_data:
            if file_data["type"] == "image":
                st.image(file_data["data"], caption="Uploaded Image", width=300)
            elif file_data["type"] == "document":
                cache_indicator = " 💾" if file_data.get("cached") else ""
                st.info(f"📄 {file_data['original_name']}{cache_indicator}")
        st.markdown(prompt)

    # Display assistant response with streaming
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        token_placeholder = st.empty()
        full_response = ""

        # Metadata tracking
        metadata = {
            "usage": {},
            "metrics": {}
        }

        try:
            # Prepare messages for API
            api_messages = []
            for msg in st.session_state.messages:
                content = []

                # Add image if present
                if "image" in msg:
                    content.append({
                        "image": {
                            "format": msg["image"]["format"],
                            "source": {
                                "bytes": msg["image"]["data"]
                            }
                        }
                    })

                # Add document if present - always use bytes
                if "document" in msg:
                    doc = msg["document"]
                    content.append({
                        "document": {
                            "format": doc["format"],
                            "name": doc["name"],
                            "source": {
                                "bytes": doc["content"]
                            }
                        }
                    })

                    # Add cache point after document if it was cached
                    if doc.get("cached", False):
                        content.append({
                            "cachePoint": {
                                "type": "default"
                            }
                        })

                # Add text
                if "text" in msg:
                    content.append({"text": msg["text"]})

                api_messages.append({
                    "role": msg["role"],
                    "content": content
                })

            # Prepare system prompt with optional cache point
            system_config = None
            if system_prompt.strip():
                system_config = [{"text": system_prompt}]

                # Add cache point for system prompt if enabled
                if enable_system_cache:
                    system_config.append({
                        "cachePoint": {
                            "type": "default"
                        }
                    })

            # Call converse_stream API
            response = bedrock_client.converse_stream(
                modelId=model_id,
                messages=api_messages,
                system=system_config,
                inferenceConfig={
                    "maxTokens": max_tokens,
                    "temperature": temperature
                }
            )

            # Process the stream
            stream = response.get('stream')
            if stream:
                for event in stream:
                    if 'contentBlockDelta' in event:
                        delta = event['contentBlockDelta']['delta']
                        if 'text' in delta:
                            text_chunk = delta['text']
                            full_response += text_chunk
                            message_placeholder.markdown(full_response + "▌")

                    elif 'messageStop' in event:
                        stop_reason = event['messageStop'].get('stopReason', 'unknown')
                        if stop_reason != 'end_turn':
                            st.info(f"ℹ️ Stop reason: {stop_reason}")

                    elif 'metadata' in event:
                        event_metadata = event['metadata']

                        # Capture usage data
                        if 'usage' in event_metadata:
                            metadata['usage'] = event_metadata['usage']
                            

                        # Capture metrics data
                        if 'metrics' in event_metadata:
                            metadata['metrics'] = event_metadata['metrics']

            # Update the final message
            message_placeholder.markdown(full_response)

            # Display metadata
            meta_parts = []

            if metadata.get('usage'):
                usage = metadata['usage']
                input_tok = usage.get('inputTokens', 0)
                output_tok = usage.get('outputTokens', 0)
                cache_read = usage.get('cacheReadInputTokens', 0)
                cache_write = usage.get('cacheWriteInputTokens', 0)

                meta_parts.append(f"Input: {input_tok:,} | Output: {output_tok:,}")

                if cache_read > 0:
                    meta_parts.append(f"💾 Cache Read: {cache_read:,}")
                if cache_write > 0:
                    meta_parts.append(f"💾 Cache Write: {cache_write:,}")

            if metadata.get('metrics'):
                metrics = metadata['metrics']
                latency = metrics.get('latencyMs', 0)
                if latency > 0:
                    meta_parts.append(f"⏱️ {latency:,}ms")

            if meta_parts:
                token_placeholder.caption(f"📊 {' | '.join(meta_parts)}")

            # Add assistant response to chat history with metadata
            st.session_state.messages.append({
                "role": "assistant",
                "text": full_response,
                "metadata": metadata
            })

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            st.error(f"❌ AWS Error ({error_code}): {error_message}")

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            st.error(traceback.format_exc())