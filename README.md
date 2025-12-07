# streamlit-strands-agent

## Strands Web Grounding Chat

A chat application built with **Streamlit** and **Strands Agent**, powered by **AWS Bedrock**, capable of:

- Conversational AI with **Claude Sonnet 4**
- Real-time web grounding via **Amazon Nova Premier**
- Image generation via **Stability AI SD 3.5 Large**
- Multi-tool agent capabilities: calculator, current time, web search, image generation

**Project Goal:**  
Enable developers to deploy AI agents that can access real-time web data, perform calculations, generate images, and answer questions interactively.

## ⚡ Features

- Multi-agent orchestration in Streamlit
- **Web Grounding**: Fetch real-time data and cite sources
- **Image Generation**: Text-to-image AI generation
- Calculator & Time Tools: Instant math and time queries
- Clean, modular architecture designed for **AI extractability**  

## Setup

### Create Virtual Environment

uv venv --python 3.12

### Activate Virtual Environment

.venv\Scripts\activate

### Install Dependencies

pip install -r requirements.txt

### Set Bedrock Credentials

set AWS_PROFILE=xxx

### Run the Application

streamlit run --server.headless=True --server.port=8501 app.py

---
## How do I use the features?

### Web Grounding
Fetch real-time news, updates, and AWS information with automatic source citations.

**Example queries:**
- What are the current AWS regions?
- Latest AI news this week
- What's happening in generative AI today?

### Image Generation
Generate images from text prompts using Stability AI.

**Example prompts:**
- Generate an image of a futuristic city
- Create a night-time scene of Tokyo
- Design a modern cloud architecture diagram

### Calculator & Time Tools
Perform calculations and query current time and date.

**Example queries:**
- What is 1234 * 5678?
- What's the current time in PST?
- Calculate 15% of 2500

---

## How does web grounding work?

Web grounding enables the AI agent to:
1. Fetch real-time information from the web
2. Cite reliable sources automatically
3. Provide up-to-date answers beyond training data

**Citations appear in the sidebar** with clickable links to sources.