from critical_dir.db_conn import get_db_conn
from critical_dir.settings import get_settings
from psycopg.rows import dict_row
import os

def helper_get_nrows(cur, tbl:str) -> int:
    cur.execute(f'SELECT COUNT(*) AS c FROM {tbl};')
    res = cur.fetchone()
    assert res is not None
    return res['c']

def helper_count_identical_rows_data_and_archive(cur, tbl_data:str, tbl_archive:str) -> int:
    # Note that data table has field 'deviceid', archive table has 'deviceid_h' with hashed IDs instead
    cur.execute(
        f"""
        SELECT COUNT(*) AS c
        FROM {tbl_data} q1
        INNER JOIN {tbl_archive} q2 ON q1._h=q2._h
        WHERE q1.latitude=q2.latitude AND q1.longitude=q2.longitude AND q1.timestamp=q2.timestamp AND q1.ts_entry_creation=q2.ts_entry_creation;
        """
    )
    res = cur.fetchone()
    assert res is not None
    return res['c']

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
    
    # test number of rows in quarantine table
    assert 0 == helper_get_nrows(cur, settings.quarantinetable)

    # get number of rows in data table
    datatable_nrows = helper_get_nrows(cur, settings.datatable)

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

    # compare data and archive tables (function returns number of rows in agreement)
    assert 8==helper_count_identical_rows_data_and_archive(cur, tbl_data=settings.datatable, tbl_archive=settings.archivetable)

def test_analyze_ingestion_archive():
    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)
    # FIXME: hard-coded table names
    assert 8==helper_get_nrows(cur, 'criticalmaps_data_archive_test_archiveon')
    assert 0==helper_get_nrows(cur, 'criticalmaps_data_archive_test_archiveoff')
    # check that there was a run of the ingestion script (especially important in the 'off' case)
    assert 1==helper_get_nrows(cur, 'criticalmaps_stats_test_archiveon')
    assert 1==helper_get_nrows(cur, 'criticalmaps_stats_test_archiveoff')


def test_analyze_idempotence(capsys):
    """
    Evaluates the test for idempotence.
    As of June-2026, this test is performed by running the same import twice.
    """
    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)

    ### get number of rows in quarantine and data table
    # FIXME: hard-coded table name
    assert 0 == helper_get_nrows(cur, 'criticalmaps_data_quarantine_test_idempotency')
    datatable_nrows = helper_get_nrows(cur, 'criticalmaps_data_test_idempotency')

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


    # compare data and archive tables (function returns number of rows in agreement)
    # FIXME: hard-coded table names
    assert 8==helper_count_identical_rows_data_and_archive(cur, tbl_data='criticalmaps_data_test_idempotency', tbl_archive='criticalmaps_data_archive_test_idempotency')

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
        assert nrows_in_file-1 == helper_get_nrows(cur, tblname)
    for tblname in ['criticalmaps_data_quarantine_test_badlat','criticalmaps_data_quarantine_test_badlng']:
        assert 1 == helper_get_nrows(cur, tblname)


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

    # compare data and archive tables (function returns number of rows in agreement)
    # FIXME: hard-coded table names
    assert (nrows_in_file-1)==helper_count_identical_rows_data_and_archive(cur, tbl_data='criticalmaps_data_test_badlat', tbl_archive='criticalmaps_data_archive_test_badlat')
    assert (nrows_in_file-1)==helper_count_identical_rows_data_and_archive(cur, tbl_data='criticalmaps_data_test_badlng', tbl_archive='criticalmaps_data_archive_test_badlng')

def test_analyze_badurl(capsys):
    conn = get_db_conn()
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    cur = conn.cursor(row_factory=dict_row)

    # FIXME: hard-coded table name

    # Check that the (expected) exception was correctly recorded in the DB
    cur.execute('SELECT exc_inphase,exc_name,COUNT(*) AS c FROM criticalmaps_stats_test_badurl GROUP BY 1,2 ORDER BY 1,2;')
    res = cur.fetchall()
    assert len(res)==1
    assert res[0]['exc_inphase']=='API access'
    # check name of the exception (we expect SSLError, but because outcome here
    # depends on external server we don't control, let's also allow ConnectionError)
    assert res[0]['exc_name'] in ['SSLError','ConnectionError']
    assert res[0]['c']==1 # ensure the exception was only fired a single time

    # there must be no data in the data tables
    for tblname in ['criticalmaps_data_quarantine_test_badurl','criticalmaps_data_test_badurl']:
        assert 0==helper_get_nrows(cur, tblname)
