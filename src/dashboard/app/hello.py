import streamlit as st

st.set_page_config(page_title="Hello", page_icon=":material/waving_hand:")
st.title("Welcome to the Critical Directions Dashboard")
st.write(
    """
    **👈 To explore the current status, select one panel from the sidebar**

    Available panels:
    * [Ingestion Statistics](/stats_ingest)
    """
)
