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

# Page configuration
st.set_page_config(
    page_title="Strands Chat App",
    page_icon="💬",
    layout="centered"
)

# Create bedrock client
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')

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

        # Run boto3 call in thread pool to avoid blocking
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

        # Get base64 image
        response_image_base64 = response_body["images"][0]
        image_bytes = base64.b64decode(response_image_base64)

        # Store in session state using Streamlit's context
        if 'generated_images' not in st.session_state:
            st.session_state.generated_images = []

        st.session_state.generated_images.append(image_bytes)

        return f"✅ Image generated successfully! (seed: {seed})"

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"❌ Error: {str(e)}\n{error_details}"

# Initialize agent
@st.cache_resource
def initialize_agent():
    bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        temperature=0.1,
    )

    agent = Agent(
        model=bedrock_model,
        #system_prompt="You are a helpful assistant. When users ask to generate, create, draw, or make images, use the generate_image tool with detailed, descriptive prompts.",
        system_prompt="You are a helpful assistant.",
        tools=[calculator, current_time, generate_image]
    )

    return agent

agent = initialize_agent()

# App title
st.title("💬 Strands Chat App")
st.caption("Powered by Claude Sonnet 4 & Stability AI Ultra")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "generated_images" not in st.session_state:
    st.session_state.generated_images = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            if message.get("text"):
                st.markdown(message.get("text"))
            st.image(message["content"], width='stretch')
        else:
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Track how many images we had before
                images_before = len(st.session_state.generated_images)

                # Call agent asynchronously
                async def get_response():
                    return await agent.invoke_async(prompt)

                response = asyncio.run(get_response())
                response_text = str(response)

                st.markdown(response_text)

                # Check if new images were generated
                images_after = len(st.session_state.generated_images)

                if images_after > images_before:
                    # Display all new images
                    for i in range(images_before, images_after):
                        image_bytes = st.session_state.generated_images[i]
                        image = Image.open(BytesIO(image_bytes))
                        st.image(image, width='stretch')

                        # Add to message history
                        st.session_state.messages.append({
                            "role": "assistant",
                            "type": "image",
                            "text": response_text,
                            "content": image
                        })
                else:
                    # Text-only response
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text
                    })

            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                import traceback
                st.code(traceback.format_exc())
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_message
                })

# Sidebar
with st.sidebar:
    st.header("Chat Controls")

    if st.button("🗑️ Clear Chat", width='stretch'):
        st.session_state.messages = []
        st.session_state.generated_images = []
        st.cache_resource.clear()
        st.rerun()

    st.metric("Messages", len(st.session_state.messages))
    st.metric("Images Generated", len(st.session_state.generated_images))

    st.divider()

    st.subheader("Model Info")
    st.text("Chat: Claude Sonnet 4")
    st.text("Image: Stability Ultra v1")
    st.text("Region: us-west-2")

    st.divider()

    with st.expander("🔍 Debug"):
        if hasattr(agent, 'tool_names'):
            st.write("Tool names:", agent.tool_names)