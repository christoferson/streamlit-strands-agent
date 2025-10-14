
import streamlit as st

chat_page = st.Page("views/chat.py", title="Chat", icon=":material/add_circle:")
#delete_page = st.Page("delete.py", title="Delete entry", icon=":material/delete:")

pg = st.navigation([chat_page])
st.set_page_config(page_title="Strands", page_icon=":material/edit:")
pg.run()
