from critical_dir.db_conn import get_db_conn
from critical_dir.settings import get_settings
from psycopg.rows import dict_row
import os

def test_demo(capsys):
    """
    First tests for ingestion script.
    After performing API request, inspect database.
    """
    # check that we see the data file
    """
    with capsys.disabled():
        os.system('ls -l /stor')
    """

    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)

    settings = get_settings()

    ### get number of rows in data table
    cur.execute(f'SELECT COUNT(*) AS c FROM {settings.datatable};')
    res = cur.fetchone()
    assert res is not None
    datatable_nrows = res['c']

    ### get number of rows from stats table
    cur.execute(f"SELECT nrows_merged FROM {settings.statstable} WHERE total_status='1';")
    res = cur.fetchall()
    # after loading one file, we expect exact one line
    assert len(res)==1
    statstable_nrows = res[0]['nrows_merged']

    """
    with capsys.disabled():
        print(res[0]['nrows_merged'])
    """

    assert statstable_nrows == datatable_nrows

    # test file describes 8 devices, so we expect 8 rows in DB
    assert 8==datatable_nrows
