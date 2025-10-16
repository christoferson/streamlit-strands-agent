
import streamlit as st

chat_page = st.Page("views/chat.py", title="Chat", icon=":material/add_circle:")
chat_stream_page = st.Page("views/chat_stream.py", title="Chat (Stream)", icon=":material/add_circle:")
boto_converse_stream_page = st.Page("views/boto_converse_stream.py", title="Converse Stream", icon=":material/add_circle:")

pg = st.navigation([chat_page, chat_stream_page, boto_converse_stream_page])
st.set_page_config(page_title="Strands", page_icon=":material/edit:")
pg.run()
