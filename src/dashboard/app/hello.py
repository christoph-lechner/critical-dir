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

def get_api_statshealthchecks(cur, *, endpoint='/myapp/api/health', ndays=30):
    cur.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN status=200 THEN 1 END), 0) AS n_ok,
            COALESCE(SUM(CASE WHEN status=500 THEN 1 END), 0) AS n_fail
        FROM api_perf_log
        WHERE ts >= NOW() - %(ndays)s*INTERVAL '1 DAYS' AND path=%(endpoint)s;
        """,
        {'endpoint': endpoint, 'ndays':ndays}
    )
    res = cur.fetchone()
    if res is None:
        raise ValueError('SQL query: unexpected result')
    return {'n_ok':res['n_ok'], 'n_failed':res['n_fail']}

def get_api_hits(cur, *, endpoint='/myapp/api/clusters', method='GET', ndays=30):
    cur.execute(
        """
        SELECT
        	COUNT(*) AS c,
	        (PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY time))/1.0e3 AS p90
        FROM api_perf_log
        WHERE
            ts >= NOW() - %(ndays)s*INTERVAL '1 DAYS'
            AND
            method=%(method)s AND path=%(endpoint)s;
        """,
        {'method':method, 'endpoint': endpoint, 'ndays':ndays}
    )
    res = cur.fetchone()
    if res is None:
        raise ValueError('SQL query: unexpected result')

    # There may be insufficient data in DB to determine response time percentile
    thres_nhits_per_day=100
    if res['c']<thres_nhits_per_day*ndays:
        # don't return percentile
        return {'n_hits': res['c'], 'response_time_p90': None}

    return {'n_hits': res['c'], 'response_time_p90': res['p90']}


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
cols = st.columns(2)
cols[0].metric('dummy', '123', '-23', border=True)
cols[1].metric('Failed ingestion runs (last 7 days)', get_ing_nfailedruns(cur), border=True)


st.write(
    """
    ## API Statistics
    Main page: [API statistics](/stats_api)
    """
)
#
cols = st.columns(2)
for ndays in [7,30]:
    stats_hits = get_api_hits(cur, ndays=ndays)
    cols[0].metric(f'Hits "/clusters" (previous {ndays} days)', stats_hits['n_hits'], border=True)
    cols[1].metric(f'Reponse Time [ms] "/clusters" (q=0.9; previous {ndays} days)', stats_hits['response_time_p90'], format='%.2f', border=True)
#
cols = st.columns(2)
for ndays in [7,30]:
    stats_hc = get_api_statshealthchecks(cur, ndays=ndays)
    cols[0].metric(f'Healthchecks OK (previous {ndays} days)', stats_hc['n_ok'], border=True)
    cols[1].metric(f'Healthchecks Failed (previous {ndays} days)', stats_hc['n_failed'], border=True)
