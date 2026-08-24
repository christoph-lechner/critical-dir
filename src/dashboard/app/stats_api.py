import psycopg
import pandas as pd
import streamlit as st
import plotly.express as px
from db_conn import get_db_conn

def get_api_stats(cur, *, endpoint='/myapp/api/clusters', method='GET'):
    cur.execute(
        """
        WITH q_agg AS(
            SELECT
                DATE_BIN('15 MINUTES', ts AT TIME ZONE 'Europe/Berlin', '2026-01-01 UTC') AS h,
                COUNT(*) AS c,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY time) AS p50,
                PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY time) AS p90
            FROM api_perf_log
            WHERE
                ts >= NOW() - %(ndays)s*INTERVAL '1 DAYS'
                AND
                method=%(method)s AND path=%(endpoint)s
            GROUP BY 1
            ORDER BY 1
        ),
        tser AS(
            SELECT
                generate_series(
                    (SELECT MIN(h) FROM q_agg),
                    (SELECT MAX(h) FROM q_agg),
                    INTERVAL '15 MINUTES'
                ) AS x
        )
        SELECT
            tser.x,
            -- if there is NO data, we report count=0 (instead of NULL)
            COALESCE(q_agg.c,0) AS c,
            -- report percentiles only when there is sufficient data
            CASE WHEN q_agg.c>=10 THEN q_agg.p50/1.0e3 ELSE NULL END AS p50,
            CASE WHEN q_agg.c>=10 THEN q_agg.p90/1.0e3 ELSE NULL END AS p90
        FROM tser
        LEFT JOIN q_agg ON tser.x=q_agg.h
        ORDER BY tser.x;
        """,
        {'method':method, 'endpoint':endpoint, 'ndays':7}
    )
    res = cur.fetchall()
    df = pd.DataFrame.from_dict(res)
    return df

# establish DB connection
conn = get_db_conn()
from psycopg.rows import dict_row
cur = conn.cursor(row_factory=dict_row)

# get the needed data
try:
    df = get_api_stats(cur)
except psycopg.errors.UndefinedTable as e:
    st.warning(
            f'''Got exception related to missing table. Remember that this dashboard requires additional data preparation.
            The message is: "{str(e)}"
            Stopping here.'''
    )
    st.stop()

if len(df.index)==0:
    st.warning('Insufficient data in database')
    st.stop()

cur.close()
conn.close()



st.write(
    """
    ## Number of API Requests
    """
)
st.line_chart(df, x='x', y='c', x_label='time stamp', y_label='API requests / 15min')

st.write(
    """
    ## API Response Times
    How long does the API server need to respond to incoming requests?
    Note that no data is indicated in the plots if there was only a small number of requests (currently less than 10 requests in 15 minutes).
    """
)
# mapping of traces and desired legend texts
traces = {
    'p50': 'Median',
    'p90': 'q=0.9',
}
# Build initial plot
fig = px.line(
        df,
        x='x',
        y=list(traces.keys())
)
# Update legend texts (default is name of column in data frame)
fig.for_each_trace(lambda t: t.update(name=traces.get(t.name,t.name)))
fig.update_layout(xaxis_title='time stamp', yaxis_title='Response Time [ms]', legend_title_text='Percentiles')
st.plotly_chart(fig, width='stretch')
