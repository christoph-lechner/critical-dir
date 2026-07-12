import streamlit as st
from db_conn import get_db_conn

def get_ing_nfailedruns(cur):
    cur.execute(
        """
        SELECT
            COUNT(*) AS c
        FROM criticalmaps_stats WHERE total_status='0' AND ts>=NOW() - INTERVAL '7 days';
        """
    )
    res = cur.fetchone()
    if res is None:
        raise ValueError('SQL query: unexpected result')
    return res['c']



conn = get_db_conn()
from psycopg.rows import dict_row
cur = conn.cursor(row_factory=dict_row)

st.set_page_config(page_title="Hello", page_icon=":material/waving_hand:")
st.title("Critical Directions Dashboard")
st.write("**👈 To explore the current status, select one panel from the sidebar**")

st.write(
    """
    ## Ingestion Statistics
    Main page: [Ingestion statistics](/stats_ingest)
    """
)
cols = st.columns(3)
cols[0].metric('Failed ingestion runs (last 7 days)', get_ing_nfailedruns(cur), border=True)
cols[1].metric('demox', '123', '-23', border=True)
cols[2].metric('demoy', '456', '111', border=True)
