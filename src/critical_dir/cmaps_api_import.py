#!/usr/bin/env python3

import time
import datetime
import signal
import threading
import queue
import sys
import argparse
from threading import Event
from pathlib import Path
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from critical_dir.cmaps_api import get_cmaps_data

import psycopg
from psycopg.rows import dict_row
from critical_dir.db_conn import get_db_conn
from critical_dir.cmaps_util import load_cmap_jsonfile

from critical_dir.settings import get_settings

@dataclass
class ProcStats:
    # no default for first two fields: we always know start time and total duration
    tstart: datetime.datetime
    total_time: float
    #
    total_status: bool = False
    #
    # The defaults of all other fields map to NULL in SQL DB
    #
    exc_inphase: str = None
    exc_name: str = None
    exc_info: str = None
    #
    api_http_response_code: int = None
    #
    fileok: bool = None
    filename: str = None
    nrows_loaded: int = None
    nrows_inserts: int = None
    nrows_updates: int = None
    nrows_quarantine: int = None


# data schema, without fields that will be added during the loading process: _h, id_run, and ts_entry_creating
datacol_ddl = \
"""
    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT
"""
def prepare_stg_table(cur, stg_table, *, temptbl=True):
    tempflag = 'TEMPORARY' if temptbl else ''
    cur.execute(
        f"""
        CREATE {tempflag} TABLE {stg_table} (
            {datacol_ddl}
        );
        """
    )

def data_add_hashes(cur, stg_dest, stg_src, *, temptbl=True):
    """
    "stg_dest" is name of temporary destination table that is to be created by this function

    This function adds two different hashes:
    . a hash for deduplication
    . a hashed deviceid (together with date in timestamp) for archive table.
    """
    tempflag = 'TEMPORARY' if temptbl else ''
    cur.execute(
        f"""
        CREATE {tempflag} TABLE {stg_dest} AS (
            SELECT
                -- Hash for deduplication
                MD5(CONCAT(CONCAT(deviceid,'_'),'-',CONCAT(timestamp,'_'))) AS _h,
                -- Hash for archive table
                MD5( CONCAT(
                    COALESCE(deviceid,'<NULL>'), '-',
                    -- For stable, locale-independent representation of the date extracted from the epoch: (i) forcing timezone UTC; (ii) using 'to_char' 
                    COALESCE(TO_CHAR((TO_TIMESTAMP(timestamp) AT TIME ZONE 'UTC')::date, 'YYYYMMDD'),'<NULL>')
                )) AS deviceid_h,
                deviceid,latitude,longitude,timestamp
            FROM {stg_src}
        );
        """
    )

def data_dedupl(cur, stg_dest, stg_src, *, temptbl=True):
    tempflag = 'TEMPORARY' if temptbl else ''
    cur.execute(
        f"""
            CREATE {tempflag} TABLE {stg_dest} AS
            WITH q AS (
                SELECT
                    _h,deviceid_h,deviceid,latitude,longitude,timestamp,
                    ROW_NUMBER() OVER(PARTITION BY _h) AS _rn
                FROM {stg_src}
            )
            SELECT
                _h,deviceid_h,deviceid,latitude,longitude,timestamp
            FROM q
            WHERE _rn=1;
        """
    )
    return cur.rowcount

def data_check_rules(*, cur, stg):
    # add new column with OK flag (initially, before testing the conditions all entries are 'ok')
    cur.execute(f'ALTER TABLE {stg} ADD COLUMN flag_ok INT;')
    cur.execute(f'UPDATE {stg} SET flag_ok=1;')

    # Rule checks
    # Note: If they fail, these checks zero flag_ok. You must NEVER set the flag to 1!
    cur.execute(f'UPDATE {stg} SET flag_ok=0 WHERE ABS(latitude)>90;')
    cur.execute(f'UPDATE {stg} SET flag_ok=0 WHERE ABS(longitude)>180;')
    # TODO: add time filter rejecting too old entries

def data_add_id_run(*, cur, stg, id_run):
    # add id_run column
    # (without foreign key constraint, the following MERGE operation
    # inserts data in table with foreign key contraint active)
    cur.execute(f'ALTER TABLE {stg} ADD COLUMN id_run BIGINT;')
    cur.execute(f'UPDATE {stg} SET id_run=%s;', (id_run,))

def data_route_and_merge(cur, *, data_table, quarantine_table, stg_table):
    def execute_merge(*, dst_table, dataok=True):
        # Note: On match: updating data values since there could be changes to the data at a later time
        cur.execute(
            f"""
            WITH q AS(
                MERGE
                INTO
                    {dst_table} AS dst
                USING
                    (SELECT * FROM {stg_table} WHERE flag_ok=%s) src
                ON
                    dst._h=src._h
                WHEN MATCHED THEN
                    UPDATE SET id_run=src.id_run,deviceid=src.deviceid, latitude=src.latitude, longitude=src.longitude, timestamp=src.timestamp
                WHEN NOT MATCHED THEN
                    INSERT VALUES (_h,id_run,deviceid,latitude,longitude,timestamp)
                RETURNING
                    -- merge_action() is new in PostgreSQL v18
                    dst._h, merge_action() AS action
            )
            SELECT
                COUNT(*) FILTER (WHERE action='INSERT') AS n_inserts,
                COUNT(*) FILTER (WHERE action='UPDATE') AS n_updates
            FROM q;
            """,
            (int(dataok),) # explicit type casting to int avoids error "psycopg.errors.UndefinedFunction: operator does not exist: integer = boolean"
        )
        res_m = cur.fetchone()
        return res_m

    res_m   = execute_merge(dst_table=data_table,       dataok=True)
    res_m_q = execute_merge(dst_table=quarantine_table, dataok=False)
    n_q = res_m_q['n_inserts']+res_m_q['n_updates']

    return res_m['n_inserts'],res_m['n_updates'],n_q


#####

def status_info_generate_id(*, cur, info_table='criticalmaps_stats_dev'):
    """
    Obtain file ID.
    Information will be added later.
    """
    cur.execute(
        f'INSERT INTO {info_table} (ts) VALUES (NULL) RETURNING id;'
    )
    res = cur.fetchone()
    return res['id']

def store_status_info(*, cur, id_run:int=None, ps: ProcStats, info_table='criticalmaps_stats_dev'):
    if not id_run:
        id_run = status_info_generate_id(cur=cur, info_table=info_table)

    cur.execute(
        'UPDATE ' +info_table+ ' SET ts=%s,total_time=%s,total_status=%s,   exc_inphase=%s,exc_name=%s,exc_info=%s,   api_http_response_code=%s,   fileok=%s,filename=%s,nrows_loaded=%s,nrows_inserts=%s,nrows_updates=%s,nrows_quarantine=%s WHERE id=%s',
        (ps.tstart,ps.total_time,ps.total_status,   ps.exc_inphase,ps.exc_name,ps.exc_info,   ps.api_http_response_code,   ps.fileok,ps.filename,ps.nrows_loaded,ps.nrows_inserts,ps.nrows_updates,ps.nrows_quarantine,   id_run)
    )

#####

@dataclass(frozen=True)
class PipelineResult:
    id_run: int
    nrows_loaded: int
    nrows_inserts: int
    nrows_updates: int
    nrows_quarantine: int
    # for testing: expose names of tables that were generated
    stg_table: str
    stg_table_hashed: str
    stg_table_dedupl: str


def run_pipeline(cur,settings,data,t0, *, temptbl=True):
    # create unique names for data staging steps
    str_t0 = t0.strftime('%Y%m%dT%H%M%S')
    stg_table = 'stg_'+str_t0
    stg_table_hashed = stg_table + '_h'
    stg_table_dedupl = stg_table + '_d'

    # Obtain ID for this ingestion run, could be used to earmark rows in data tables etc.
    # (there was no need to get it earlier, because only now we begin to actually insert data)
    id_run = status_info_generate_id(cur=cur, info_table=settings.statstable)

    # prepare and populate staging table
    nrows_loaded=0
    prepare_stg_table(cur, stg_table, temptbl=temptbl)
    for d in data:
        nrows_loaded+=1
        cur.execute(
            'INSERT INTO ' +stg_table+ ' (deviceid,latitude,longitude,timestamp) VALUES (%s,%s,%s,%s)',
            (d.device, d.latitude, d.longitude, d.timestamp)
        )

    data_add_hashes(cur, stg_table_hashed, stg_table, temptbl=temptbl)
    data_dedupl(cur, stg_table_dedupl, stg_table_hashed, temptbl=temptbl)
    data_check_rules(cur=cur, stg=stg_table_dedupl) # adds column with "OK flag" to the table
    data_add_id_run(cur=cur, stg=stg_table_dedupl, id_run=id_run)
    nrows_inserts,nrows_updates,nrows_quarantine = data_route_and_merge(
            cur,
            data_table=settings.datatable,
            quarantine_table=settings.quarantinetable,
            stg_table=stg_table_dedupl
    )

    return PipelineResult(
        id_run,
        nrows_loaded=nrows_loaded, nrows_inserts=nrows_inserts, nrows_updates=nrows_updates, nrows_quarantine=nrows_quarantine,
        stg_table=stg_table, stg_table_hashed=stg_table_hashed, stg_table_dedupl=stg_table_dedupl
    )


#####

# signal handler
done_event = Event()
stop_event = Event()
def sighandler_term(signum, frame):
    done_event.set()
    stop_event.set()

#####

def download_worker(*, f_heartbeat: Callable=None, api_url=None):
    """
    Returns True when everything was OK.
    """
    settings = get_settings()

    def get_fn(*, fn_extension:str='json'):
        tnow = datetime.datetime.now()
        tdatestr = tnow.strftime('%Y%m%d')
        tnowstr = tnow.strftime('%Y%m%dT%H%M%S_%f') # '%f' is always 6 digits wide and padded w/ leading zeros
        # create data directory if needed (using per-day directories for better file organization)
        datadir = settings.api_downloader_json_outdir / tdatestr
        datadir.mkdir(parents=False, exist_ok=True)
        # return filename
        return datadir / ('data_'+tnowstr+'.'+fn_extension)

    def put_info_file(txt, *, dupl_to_stdout=False):
        if dupl_to_stdout:
            print(txt)
        fn = get_fn(fn_extension='txt')
        print(f'going to write infos to file {fn}')
        with open(fn,'w') as fout:
            fout.write(txt)


    tprocstart = datetime.datetime.now()

    # establish DB connection
    try:
        conn = get_db_conn()
        # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
        cur = conn.cursor(row_factory=dict_row)
    except Exception as e:
        print('*** Could not establish DB connection ***')
        put_info_file(traceback.format_exc(), dupl_to_stdout=True)
        return False

    try:
        # TODO: add timeouts here
        fn_out = get_fn()
        print(f'Downloading data to file {fn_out} ...')
        # passing optional parameter using 'kwargs', prevents overriding default value given in function def
        kwargs = {}
        if api_url:
            kwargs = {'api_url': api_url}
        data = get_cmaps_data(**kwargs)
        with open(fn_out,'w') as fout:
            fout.write(data)
        
        # Heartbeat signaling everything is OK. The data was written stored in a file, so even if the following DB ingestion fails, we have the data.
        if f_heartbeat:
            f_heartbeat()
        #if status['healthcheck']:
        #    status['healthcheck'].heartbeat()
    except Exception as e:
        # Design idea to be implemented: Networking issues while getting the data are ok (this would also include any "bad" HTTP status codes such as 500),
        # consider to re-raise file I/O issues to stop the program (but then a watchdog has to start another instance so that data acquisition goes on)
        print('*** Data download resulted in exception ***')
        put_info_file(traceback.format_exc(), dupl_to_stdout=True)
        procstats = ProcStats(
                tstart=tprocstart,
                total_time = (datetime.datetime.now() - tprocstart).total_seconds(),
                total_status = False,
                exc_inphase='API access',
                exc_name = type(e).__qualname__,
                exc_info = traceback.format_exc(),
                # 2026-06-29: at the moment not assigning HTTP response code
                filename = str(fn_out),
        )
        # print(procstats)

        # Note: There must not have been any SQL write access -- except storing these infos
        store_status_info(cur=cur, ps=procstats, info_table=settings.statstable)
        conn.commit()
        return False

    # DB operations are in third try/catch block to make the program more robust
    # (for instance if a single operation fails for whatever reason)
    try:
        data = load_cmap_jsonfile(fn_out)
        res_pipeline = run_pipeline(cur, settings, data, tprocstart)
        procstats = ProcStats(
                tstart=tprocstart,
                total_time = (datetime.datetime.now() - tprocstart).total_seconds(),
                total_status = True,
                # 2026-06-29: at the moment not assigning HTTP response code
                filename = str(fn_out),
                fileok = True,
                nrows_loaded     = res_pipeline.nrows_loaded,
                nrows_inserts    = res_pipeline.nrows_inserts,
                nrows_updates    = res_pipeline.nrows_updates,
                nrows_quarantine = res_pipeline.nrows_quarantine
        )
        store_status_info(cur=cur, id_run=res_pipeline.id_run, ps=procstats, info_table=settings.statstable)

        conn.commit()
    except Exception as e:
        print('*** DB operations resulted in exception ***')
        put_info_file(traceback.format_exc(), dupl_to_stdout=True)
        procstats = ProcStats(
                tstart=tprocstart,
                total_time = (datetime.datetime.now() - tprocstart).total_seconds(),
                total_status = False,
                exc_inphase='DB access',
                exc_name = type(e).__qualname__,
                exc_info = traceback.format_exc(),
                # 2026-06-29: at the moment not assigning HTTP response code
                filename = str(fn_out),
        )
        # print(procstats)

        # Here, we don't know which part of the DB operations failed
        # -> rollback to be one the safe side
        conn.rollback()
        store_status_info(cur=cur, id_run=id_run, ps=procstats, info_table=settings.statstable)
        conn.commit()
        return False

    return True



def t_download_thread(*, stop_event, q_retcode: queue.Queue=None, f_heartbeat: Callable=None, test_single_request=False, override_api_url=None):
    def ceil_min(dt):
        return dt.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    def wait_until(dt):
        """
        Returns True if we received a stop signal
        """
        deltat = tnext - datetime.datetime.now()
        deltat = deltat.total_seconds()
        while deltat>0:
            # break wait down into short waits to make it responsive (I think a sleep cannot be interrupted by a signal in Python)
            if deltat>3:
                deltat = 3
            # print(f'waiting for {deltat:.1f} seconds ...')
            time.sleep(deltat)
            if stop_event.is_set():
                # print('got SIGTERM/SIGINT -> stopping')
                return True
            deltat = tnext - datetime.datetime.now()
            deltat = deltat.total_seconds()
        return False

    if f_heartbeat:
        if not callable(f_heartbeat):
            raise ValueError('if specified, value has to be "callable"')

    # prepare arguments for worker
    kwargs = {}
    if f_heartbeat:
        kwargs['f_heartbeat'] = f_heartbeat
    if override_api_url:
        kwargs['api_url'] = override_api_url

    if test_single_request:
        # special case for automatic testing
        rc = download_worker(**kwargs)
        if q_retcode:
            q_retcode.put(rc)
        return

    # schedule first request to happen at the start of the next minute
    tnext = ceil_min( datetime.datetime.now() )
    print(f'About to enter main loop, first API access scheduled for {tnext}')
    while True:
        wait_until(tnext)
        tnext = tnext + datetime.timedelta(seconds=30)
        if stop_event.is_set():
            print('got SIGTERM/SIGINT -> stopping')
            break

        # We don't process the status code of the individual operation,
        # instead we try again regardless of good/bad status
        download_worker(**kwargs)

    if q_retcode:
        q_retcode.put(True)
    return


def mainloop(*, healthcheck=None, override_api_url=None, test_one_request=False):
    t_kw = {'stop_event':stop_event}
    if healthcheck:
        f_heartbeat = healthcheck.heartbeat
        # Only passing on function that signals heartbeat (and not the entire data structure!),
        # because the only thing this function does is to manipulate a thread-safe object
        t_kw['f_heartbeat'] = f_heartbeat

    if override_api_url:
        print(f'overriding API URL to {override_api_url}')
        t_kw['override_api_url'] = override_api_url

    testmode = test_one_request
    if testmode:
        print('Running in a TEST MODE: only sending a single API request')
        t_kw['test_single_request'] = True

    q_rc = queue.Queue()
    t_kw['q_retcode'] = q_rc

    t_dl = threading.Thread(target=t_download_thread, kwargs=t_kw)
    t_dl.start()

    """
    if not testmode:
        # FIXME 2026-06-29: it appears this loop is not needed (anymore) -> think about it
        while True:
            if done_event.is_set():
                print('main loop: got SIGTERM/SIGINT -> stopping')
                break

            # short sleeps to avoid busy waiting
            time.sleep(1)
    """

    t_dl.join()
    if healthcheck:
        healthcheck.stop_server()

    try:
        status = q_rc.get(timeout=60)
    except queue.Empty:
        # timeout -> consider as bad status code
        status = False

    return status

def main():
    cfg = {
        # For HTTP-based health checking (if enabled). Age of last event seen that is still "good". Note that this cannot be changed at runtime.
        'healthcheck_maxage': 900,
    }

    parser = argparse.ArgumentParser()

    # HTTP-based monitoring of the current status
    # You get HTTP status 200 if everything is OK (events are being processed),
    # and HTTP status 500 if there is an issue.
    # Use for example "curl --head http://localhost:9999/check" to check.
    parser.add_argument('--status_port', type=int, help='simple HTTP server for remote status checking', default=None)
    parser.add_argument('--override_api_url', type=str, help='override API URL to access (for automatic testing, can be http/https/file URL)')
    parser.add_argument('--test_one_request', action='store_true', help='Test mode (for automatic testing): Do not loop forever, only a single request is sent')
    args = parser.parse_args()

    kwargs = {}
    if args.override_api_url:
        kwargs['override_api_url'] = args.override_api_url
    if args.test_one_request:
        kwargs['test_one_request'] = args.test_one_request
    if args.status_port:
        from critical_dir.healthcheck import Healthcheck
        # After the maximum age has been reached, the status will transition
        # from OK to error.
        # Note that there will be HTTP 500 until after the first successful data download
        my_healthcheck = Healthcheck(http_port=args.status_port, max_age=cfg['healthcheck_maxage'])
        my_healthcheck.start_server()
        kwargs['healthcheck'] = my_healthcheck

    # Install signal handlers
    # SIGTERM is handled for graceful termination
    # SIGINT  is handled for graceful termination (user pressed <Ctrl>-<C>)
    signal.signal(signal.SIGTERM, sighandler_term)
    signal.signal(signal.SIGINT,  sighandler_term)

    status = mainloop(**kwargs)
    if status:
        sys.exit(0)
    sys.exit(1)

if __name__=='__main__':
    main()
