import streamlit as st
from strands import Agent
from strands.models import BedrockModel

# Page configuration
st.set_page_config(
    page_title="Strands Chat App",
    page_icon="💬",
    layout="centered"
)

# Initialize the Bedrock model and agent
@st.cache_resource
def initialize_agent():
    bedrock_model = BedrockModel(
        model_id="global.anthropic.claude-sonnet-4-20250514-v1:0",
        region_name="us-east-1",
        temperature=0.1,
    )

    agent = Agent(
        model=bedrock_model,
        system_prompt="You are a helpful assistant. Be concise and friendly."
    )

    return agent

# Initialize agent
agent = initialize_agent()

# App title
st.title("💬 Strands Chat App")
st.caption("Powered by Claude Sonnet 4 via AWS Bedrock")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize agent conversation state
if "agent_initialized" not in st.session_state:
    st.session_state.agent_initialized = True

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get agent response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = agent(prompt)
                st.markdown(response)

                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_message = f"Error: {str(e)}"
                st.error(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

# Sidebar with controls
with st.sidebar:
    st.header("Chat Controls")


    # Display conversation count
    st.metric("Messages", len(st.session_state.messages))

    st.divider()

    # Model information
    st.subheader("Model Info")
    st.text("Model: Claude Sonnet 4")
    st.text("Temperature: 0.3")
    st.text("Region: us-east-1")

    st.divider()

