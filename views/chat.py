import streamlit as st
from strands import Agent, tool
from strands.models import BedrockModel
import boto3
import json
import base64
from io import BytesIO
from PIL import Image
import random

# Page configuration
st.set_page_config(
    page_title="Strands Chat App",
    page_icon="💬",
    layout="centered"
)

# Create bedrock client (outside the tool function)
bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')

@tool
def generate_image(prompt: str, aspect_ratio: str = "1:1") -> str:
    """
    Generate an image using Stability AI based on a text description.

    Use this tool when users ask you to create, generate, draw, make, or produce images.
    The tool connects to Stability AI's image generation service via AWS Bedrock and
    creates high-quality images based on detailed text descriptions.

    This tool is ideal for:
    - Creating visual representations of concepts or ideas
    - Generating artwork, illustrations, or designs
    - Visualizing scenes, objects, or characters described in text
    - Producing custom images for any creative purpose

    The tool returns a success message when the image is generated, and the image
    will be automatically displayed in the chat interface.

    Args:
        prompt: Detailed text description of the image to generate. Be as descriptive
                as possible for best results. Include details about style, colors,
                composition, lighting, and mood.
                Example: "A futuristic cityscape at sunset with flying cars, neon signs,
                and towering skyscrapers reflecting golden light"
        aspect_ratio: Image aspect ratio. Options: "1:1" (square), "16:9" (landscape),
                     "9:16" (portrait), "21:9" (ultrawide), "2:3", "3:2", "4:5", "5:4"
                     Default: "1:1"

    Returns:
        str: A success message indicating the image was generated, including the random
             seed used for generation (useful for reproducing similar results)
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

        response = bedrock_runtime.invoke_model(
            modelId="stability.sd3-5-large-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request)
        )

        response_body = json.loads(response.get("body").read())
        finish_reason = response_body.get("finish_reasons")[0]

        if finish_reason is not None:
            return f"Image generation error: {finish_reason}"

        # Get base64 image
        response_image_base64 = response_body["images"][0]
        image_bytes = base64.b64decode(response_image_base64)

        # Store in session state
        st.session_state.generated_image = image_bytes

        return f"Image generated successfully with seed {seed}. The image shows: {prompt[:100]}..."

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error generating image: {str(e)}\n{error_details}"

# Initialize agent
@st.cache_resource
def initialize_agent():
    bedrock_model = BedrockModel(
        #model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",
        model_id ="global.anthropic.claude-opus-4-5-20251101-v1:0",
        region_name="us-east-1",
        temperature=0.1,
    )

    agent = Agent(
        model=bedrock_model,
        system_prompt="""You are a helpful assistant with image generation capabilities. 

When users ask you to generate, create, draw, make, or produce images, you MUST use the generate_image tool. Always provide detailed, descriptive prompts to the tool for best results.""",
        tools=[generate_image]
    )

    return agent

agent = initialize_agent()

# App title
st.title("💬 Strands Chat App")
st.caption("Powered by Claude Sonnet 4 & Stability AI")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "generated_image" not in st.session_state:
    st.session_state.generated_image = None

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message.get("type") == "image":
            if message.get("text"):
                st.markdown(message.get("text"))
            st.image(message["content"], use_container_width=True)
        else:
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Clear previous image
                st.session_state.generated_image = None

                # Call agent
                response = agent(prompt)
                response_text = str(response)

                # Display text
                st.markdown(response_text)

                # Check if image was generated
                if st.session_state.generated_image:
                    image = Image.open(BytesIO(st.session_state.generated_image))
                    st.image(image, use_container_width=True)

                    # Add to history with image
                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "image",
                        "text": response_text,
                        "content": image
                    })
                else:
                    # Add text-only to history
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

    # Clear chat button
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.generated_image = None
        st.cache_resource.clear()
        st.rerun()

    # Display conversation count
    st.metric("Messages", len(st.session_state.messages))

    st.divider()

    # Model information
    st.subheader("Model Info")
    st.text("Chat: Claude Sonnet 4")
    st.text("Image: Stability Core v1")
    st.text("Region: us-west-2")

    st.divider()

    # Debug
    with st.expander("🔍 Debug"):
        st.write("Agent object:", agent)
        st.write("Has tools attr:", hasattr(agent, 'tools'))
        st.write("Has tool_names attr:", hasattr(agent, 'tool_names'))

        if hasattr(agent, 'tool_names'):
            st.write("Tool names:", agent.tool_names)

        if hasattr(agent, 'tool_registry'):
            st.write("Tool registry:", agent.tool_registry)
            try:
                st.write("All tools config:", agent.tool_registry.get_all_tools_config())
            except:
                pass