import pandas as pd
import streamlit as st
from db_conn import get_db_conn

def get_exc_stats(cur):
    cur.execute(
        """
        SELECT
            exc_inphase,exc_name,COUNT(*) AS c, MAX(ts) AS last_seen
        FROM criticalmaps_stats
        GROUP BY 1,2
        ORDER BY 1,2;
        """
    )
    res = cur.fetchall()
    df = pd.DataFrame.from_dict(res)
    return df

def get_ing_nruns(cur):
    cur.execute(
        """
        SELECT
            DATE(ts) AS d,
            COALESCE(SUM(CASE WHEN total_status='1' THEN 1 END), 0) AS n_success,
            COALESCE(SUM(CASE WHEN total_status='0' THEN 1 END), 0) AS n_fail
        FROM criticalmaps_stats
        GROUP BY 1
        ORDER BY 1 DESC;
        """
    )
    res = cur.fetchall()
    df = pd.DataFrame.from_dict(res)
    return df

def get_ing_devstats(cur):
    cur.execute(
        """
        SELECT
            DATE_TRUNC('HOUR', ts AT TIME ZONE 'Europe/Berlin') AS d,
            MIN(nrows_loaded) AS min,
            MAX(nrows_loaded) AS max
        FROM criticalmaps_stats
        GROUP BY 1
        ORDER BY 1;
        """
    )
    res = cur.fetchall()
    df = pd.DataFrame.from_dict(res)
    return df


st.write(
    """
    # Ingestion Statistics
    """
)

conn = get_db_conn()
from psycopg.rows import dict_row
cur = conn.cursor(row_factory=dict_row)

st.write(
    """
    ## Exceptions
    In case of a successful ingestion run, the fields `exc_inphase` and `exc_name` are both None, corresponding to **no** exception.
    """
)
df = get_exc_stats(cur)
st.dataframe(df)

st.write(
    """
    ## Number of Runs
    """
)
df = get_ing_nruns(cur)
st.line_chart(df, x='d', y='n_success', x_label='date', y_label='successful runs / day')
st.line_chart(df, x='d', y='n_fail', x_label='date', y_label='Failed runs / day')


st.write(
    """
    ## Number of Devices Seen: Maximum/Minimum
    """
)
import plotly.graph_objects as go
df = get_ing_devstats(cur)
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=df['d'],
        y=df['max'],
        mode='lines',
        line=dict(color='royalblue'),
        name='Maximum',
    )
)
fig.add_trace(
    go.Scatter(
        x=df['d'],
        y=df['min'],
        mode='lines',
        line=dict(color='royalblue'),
        fill='tonexty',
        fillcolor="rgba(65, 105, 225, 0.2)",
        name='Minimum',
    )
)
fig.update_xaxes(title_text='date')
fig.update_yaxes(title_text='# devices')
fig.update_layout(hovermode='x unified') # one tooltip for all traces
st.plotly_chart(fig, width='stretch')
