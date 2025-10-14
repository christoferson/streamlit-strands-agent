# streamlit-strands-agent

A chat application built with Streamlit and Strands Agent, powered by AWS Bedrock.

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