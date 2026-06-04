#!/usr/bin/env python3

import time
import datetime
import signal
import threading
import argparse
from threading import Event
from pathlib import Path
import traceback
from collections.abc import Callable
from critical_dir.cmaps_api import get_cmaps_data

import psycopg
from psycopg.rows import dict_row
from critical_dir.db_conn import get_db_conn
from critical_dir.cmaps_util import load_cmap_jsonfile

from critical_dir.settings import settings

"""
Configuration of data output directory via environment variable
"""

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
args = parser.parse_args()

if args.status_port:
    # import here: break early when there are missing dependencies
    from critical_dir.healthcheck import Healthcheck

# based on loader_radverkehr.py
# data schema, without _h field (to be added as part of loading process), without ts_entry_creating
datacol_ddl = \
"""
    deviceid TEXT,
    longitude FLOAT,
    latitude FLOAT,
    timestamp INT
"""
def prepare_stg_table(cur, stg_table):
    #cur.execute(
    #    f"""
    #    CREATE TEMPORARY TABLE {stg_table} (
    #        {datacol_ddl}
    #    );
    #    """
    #)
    cur.execute(
        f"""
        CREATE TEMPORARY TABLE {stg_table} (
            {datacol_ddl}
        );
        """
    )

def data_add_hashes(cur, stg_dest, stg_src):
    """
    "stg_dest" is name of temporary destination table that is to be created by this function
    """
    cur.execute(
        f"""
        CREATE TEMPORARY TABLE {stg_dest} AS (
            SELECT
                MD5(CONCAT(CONCAT(deviceid,'_'),'-',CONCAT(timestamp,'_'))) AS _h,
                deviceid,longitude,latitude,timestamp
            FROM {stg_src}
        );
        """
    )

def data_dedupl(cur, stg_dest, stg_src):
    cur.execute(
        f"""
            CREATE TEMPORARY TABLE {stg_dest} AS
            WITH q AS (
                SELECT
                    *, ROW_NUMBER() OVER(PARTITION BY _h) AS _rn
                FROM {stg_src}
            )
            SELECT
                _h,deviceid,longitude,latitude,timestamp
            FROM q
            WHERE _rn=1;
        """
    )
    return cur.rowcount


def data_merge(cur, *, data_table, stg_table):
    # Note: On match: updating data values since there could be changes to the data at a later time
    cur.execute(
        f"""
        MERGE
        INTO
            {data_table} AS dst
        USING
            {stg_table} AS src
        ON
            dst._h=src._h
        WHEN MATCHED THEN
            UPDATE SET deviceid=src.deviceid, longitude=src.longitude, latitude=src.latitude, timestamp=src.timestamp
        WHEN NOT MATCHED THEN
            INSERT VALUES (_h,deviceid,longitude,latitude,timestamp);
        """
    )
    return cur.rowcount

#####

# signal handler
done_event = Event()
stop_event = Event()
def sighandler_term(signum, frame):
    done_event.set()
    stop_event.set()

#####

def t_download_worker(*,stop_event, f_heartbeat: Callable=None):
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

    def get_fn():
        tnow = datetime.datetime.now()
        tdatestr = tnow.strftime('%Y%m%d')
        tnowstr = tnow.strftime('%Y%m%dT%H%M%S_%f') # '%f' is always 6 digits wide and padded w/ leading zeros
        # create data directory if needed (using per-day directories for better file organization)
        datadir = settings.api_downloader_json_outdir / tdatestr
        datadir.mkdir(parents=False, exist_ok=True)
        # return filename
        return datadir / ('data_'+tnowstr+'.json')

    if f_heartbeat:
        if not callable(f_heartbeat):
            raise ValueError('if specified, value has to be "callable"')

    # establish DB connection
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    conn = get_db_conn()
    cur = conn.cursor(row_factory=dict_row)

    # schedule first request to happen at the start of the next minute
    tnext = ceil_min( datetime.datetime.now() )
    print(f'About to enter main loop, first API access scheduled for {tnext}')
    while True:
        wait_until(tnext)
        tnext = tnext + datetime.timedelta(seconds=30)
        if stop_event.is_set():
            print('got SIGTERM/SIGINT -> stopping')
            break

        try:
            # TODO: add time outs here
            fn_out = get_fn()
            print(f'Downloading data to file {fn_out} ...')
            data = get_cmaps_data()
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
            print(traceback.format_exc())
            continue

        # DB operations are in second try/catch block to make the program more robust (for instance if a single operation fails for whatever reason)
        # TODO: add provisions for DB connection going down.
        try:
            # create unique names for data staging steps
            t0 = datetime.datetime.now()
            str_t0 = t0.strftime('%Y%m%dT%H%M%S')
            stg_table = 'stg_'+str_t0
            stg_table_hashed = stg_table + '_h'
            stg_table_dedupl = stg_table + '_d'

            # prepare staging table
            data,_ = load_cmap_jsonfile(fn_out)
            prepare_stg_table(cur, stg_table)
            for d in data:
                cur.execute(
                    'INSERT INTO ' +stg_table+ ' (deviceid,longitude,latitude,timestamp) VALUES (%s,%s,%s,%s)',
                    (d['device'],d['longitude'],d['latitude'],d['timestamp'])
                )

            data_add_hashes(cur, stg_table_hashed, stg_table)
            data_dedupl(cur, stg_table_dedupl, stg_table_hashed)
            data_merge(cur, data_table=settings.datatable, stg_table=stg_table_dedupl)

            conn.commit()
        except Exception as e:
            print('*** DB operations resulted in exception ***')
            print(traceback.format_exc())
            continue


def mainloop(*, status):
    t_kw = {'stop_event':stop_event}
    if status['healthcheck']:
        f_heartbeat = status['healthcheck'].heartbeat
        # Only passing on function that signals heartbeat (and not the entire data structure!),
        # because the only thing this function does is to manipulate a thread-safe object
        t_kw['f_heartbeat'] = f_heartbeat

    t_dl = threading.Thread(target=t_download_worker, kwargs=t_kw)
    t_dl.start()

    while True:
        if done_event.is_set():
            print('main loop: got SIGTERM/SIGINT -> stopping')
            break

        # short sleeps to avoid busy waiting
        time.sleep(1)

    t_dl.join()
    if status['healthcheck']:
        status['healthcheck'].stop_server()

    return

def main():
    status={}
    status['healthcheck'] = None
    if args.status_port:
        # After the maximum age has been reached, the status will transition
        # from OK to error.
        # Note that there will be HTTP 500 until after the first successful data download
        status['healthcheck'] = Healthcheck(http_port=args.status_port, max_age=cfg['healthcheck_maxage'])
        status['healthcheck'].start_server()

    # Install signal handlers
    # SIGTERM is handled for graceful termination
    # SIGINT  is handled for graceful termination (user pressed <Ctrl>-<C>)
    signal.signal(signal.SIGTERM, sighandler_term)
    signal.signal(signal.SIGINT,  sighandler_term)

    mainloop(status=status)

if __name__=='__main__':
    main()
