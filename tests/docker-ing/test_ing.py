from critical_dir.db_conn import get_db_conn
from critical_dir.settings import get_settings
from psycopg.rows import dict_row
import os

def test_analyze_ingestion(capsys):
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

    ### get number of rows from stats table (and test that there were only INSERTs)
    cur.execute(f"SELECT nrows_inserts,nrows_updates,nrows_quarantine FROM {settings.statstable} WHERE total_status='1';")
    res = cur.fetchall()
    # after loading one file, we expect exact one line
    assert len(res)==1
    assert 0==res[0]['nrows_updates']
    assert 0==res[0]['nrows_quarantine']
    statstable_nrows = res[0]['nrows_inserts']

    assert statstable_nrows == datatable_nrows

    # test file describes 8 devices, so we expect 8 rows in DB
    assert 8==datatable_nrows

def test_analyze_idempotence(capsys):
    """
    Evaluates the test for idempotence.
    As of June-2026, this test is performed by running the same import twice.
    """
    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)

    ### get number of rows in data table
    # FIXME: hard-coded table name
    cur.execute(f'SELECT COUNT(*) AS c FROM criticalmaps_data_test_idempotency;')
    res = cur.fetchone()
    assert res is not None
    datatable_nrows = res['c']

    # test file describes 8 devices, so we expect 8 rows in DB
    nrows_expected = 8
    assert nrows_expected==datatable_nrows

    ### test that there were actually two successful runs...
    cur.execute(f"SELECT COUNT(*) AS c FROM criticalmaps_stats_test_idempotency WHERE total_status='1';")
    res = cur.fetchone()
    assert res is not None
    statstable_nrows = res['c']
    assert 2==statstable_nrows

    ### verify that operation that came first resulted in only INSERTs, second operation only UPDATEs (same dataset)
    # FIXME: hard-coded table name
    cur.execute(f"SELECT ts,nrows_inserts,nrows_updates,nrows_quarantine FROM criticalmaps_stats_test_idempotency WHERE total_status='1' ORDER BY ts ASC;")
    res = cur.fetchall()
    assert len(res)==2
    #with capsys.disabled():
    #    print(res)

    assert res[0]['nrows_inserts']==nrows_expected
    assert res[0]['nrows_updates']==0
    assert res[0]['nrows_quarantine']==0
    assert res[1]['nrows_inserts']==0
    assert res[1]['nrows_updates']==nrows_expected
    assert res[1]['nrows_quarantine']==0

def test_analyze_badlatlng(capsys):
    """
    Evaluates the test with bad latitude/longitude.
    """
    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)

    # rows in file (for this test, one row is violating constraints)
    nrows_in_file = 8

    # FIXME: hard-coded table names
    for tblname in ['criticalmaps_data_test_badlat','criticalmaps_data_test_badlng']:
        cur.execute(f'SELECT COUNT(*) AS c FROM {tblname};')
        res = cur.fetchone()
        assert res is not None
        assert res['c'] == nrows_in_file-1


    # FIXME: hard-coded table names
    for tblname in ['criticalmaps_stats_test_badlat','criticalmaps_stats_test_badlng']:
        cur.execute(f"SELECT ts,nrows_inserts,nrows_updates,nrows_quarantine FROM {tblname} WHERE total_status='1';")
        res = cur.fetchall()
        assert len(res)==1
        #with capsys.disabled():
        #    print(res)

        assert res[0]['nrows_inserts']==nrows_in_file-1
        assert res[0]['nrows_updates']==0
        assert res[0]['nrows_quarantine']==1
