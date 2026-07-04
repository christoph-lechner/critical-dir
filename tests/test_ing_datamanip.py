# 'dbconn' test fixture defined in conftest.py

from critical_dir.cmaps_api_import import run_pipeline
from critical_dir.cmaps_util import DeviceUpdate
from critical_dir.settings import Settings
import datetime

def helper_prepare_and_run(cur, data):
    # prepare DB structure
    with open('doc/schema.sql','r') as fin:
        r = fin.read()
    cur.execute(r)

    # settings: just the minimum amount of valid parameter values
    settings = Settings(
            pg_dsn='postgres://dev@not_a_valid_server:42/not_a_valid_db',
            img_dir='/',
            api_downloader_json_outdir='/',

            statstable='criticalmaps_stats',
            datatable='criticalmaps_data',
            quarantinetable='criticalmaps_data_quarantine',
    )
    t0 = datetime.datetime.now()
    res_pipeline = run_pipeline(cur, settings, data, t0, temptbl=False)
    return res_pipeline,settings

def helper_count_rows(cur, tbl:str) -> int:
    cur.execute(f'SELECT COUNT(*) AS c FROM {tbl};')
    res = cur.fetchone()
    assert res is not None
    return res['c']


def test_data_nodata(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    data = []
    res_pipeline,settings = helper_prepare_and_run(cur,data)
    assert 0==helper_count_rows(cur, tbl=settings.datatable)
    assert 0==helper_count_rows(cur, tbl=settings.quarantinetable)

def test_data_good(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    data = [
        DeviceUpdate(device='dev1', latitude=12.0, longitude=34.0, timestamp=123),
        DeviceUpdate(device='dev2', latitude=12.0, longitude=34.0, timestamp=123)
    ]
    res_pipeline,settings = helper_prepare_and_run(cur,data)
    assert 2==helper_count_rows(cur, tbl=settings.datatable)
    assert 0==helper_count_rows(cur, tbl=settings.quarantinetable)

def test_data_duplid(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    """
    Deduplication is based on combining and hashing fields 'deviceID' and 'timestamp'
    -> only one row should survive
    """
    data = [
        DeviceUpdate(device='dev1', latitude=12.0, longitude=34.0, timestamp=123),
        DeviceUpdate(device='dev1', latitude=23.0, longitude=45.0, timestamp=123)
    ]
    res_pipeline,settings = helper_prepare_and_run(cur,data)

    # test evolution of data in pipeline
    assert 2==helper_count_rows(cur, tbl=res_pipeline.stg_table)
    assert 1==helper_count_rows(cur, tbl=res_pipeline.stg_table_dedupl)

    assert 1==helper_count_rows(cur, tbl=settings.datatable)
    assert 0==helper_count_rows(cur, tbl=settings.quarantinetable)

def test_filter_latlng_ok(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    data = [
        DeviceUpdate(device='dev0', latitude=0.0,   longitude=0.0,    timestamp=123),
        DeviceUpdate(device='dev1', latitude=90.0,  longitude=0.0,    timestamp=123),
        DeviceUpdate(device='dev2', latitude=-90.0, longitude=0.0,    timestamp=123),
        DeviceUpdate(device='dev3', latitude=0.0,   longitude=180.0,  timestamp=123),
        DeviceUpdate(device='dev4', latitude=0.0,   longitude=-180.0, timestamp=123)
    ]
    res_pipeline,settings = helper_prepare_and_run(cur,data)

    assert 5==helper_count_rows(cur, tbl=settings.datatable)
    assert 0==helper_count_rows(cur, tbl=settings.quarantinetable)

def test_filter_lat_bad(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    eps = 1.0e-6 # incoming data is integer (values multiplied by 1E6)
    data = [
        DeviceUpdate(device='dev0', latitude=0.0,       longitude=0.0, timestamp=123),
        DeviceUpdate(device='dev1', latitude=90.0+eps,  longitude=0.0, timestamp=123),
        DeviceUpdate(device='dev2', latitude=-90.0-eps, longitude=0.0, timestamp=123)
    ]
    res_pipeline,settings = helper_prepare_and_run(cur,data)

    assert 1==helper_count_rows(cur, tbl=settings.datatable)
    assert 2==helper_count_rows(cur, tbl=settings.quarantinetable)

def test_filter_lng_bad(dbconn, capsys):
    from psycopg.rows import dict_row
    cur = dbconn.cursor(row_factory=dict_row)

    eps = 1.0e-6 # incoming data is integer (values multiplied by 1E6)
    data = [
        DeviceUpdate(device='dev0', latitude=0.0,       longitude=0.0,        timestamp=123),
        DeviceUpdate(device='dev1', latitude=0.0,       longitude=180.0+eps,  timestamp=123),
        DeviceUpdate(device='dev2', latitude=0.0,       longitude=-180.0-eps, timestamp=123)
    ]
    res_pipeline,settings = helper_prepare_and_run(cur,data)

    assert 1==helper_count_rows(cur, tbl=settings.datatable)
    assert 2==helper_count_rows(cur, tbl=settings.quarantinetable)
