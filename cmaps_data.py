#!/usr/bin/env python3

import time
import datetime
import signal
import threading
import argparse
from threading import Event
from pathlib import Path
from cmaps_api import get_cmaps_data

import psycopg
from psycopg.rows import dict_row
from db_conn import get_db_conn
from cmaps_util import load_cmap_jsonfile



cfg = {
    # data goes here (specify absolute paths!)
    'datadir': Path('/home/cl/work/criticalmaps--richtungspfeil/cmdata/'),

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
    from healthcheck import Healthcheck

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

def t_download_worker(*,stop_event):
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
        tnowstr = tnow.strftime('%Y%m%dT%H%M%S_%f') # '%f' is always 6 digits wide and padded w/ leading zeros
        return cfg['datadir'] / ('data_'+tnowstr+'.json')

    # establish DB connection
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    conn = get_db_conn()
    cur = conn.cursor(row_factory=dict_row)

    # schedule first request to happen at the start of the next minute
    tnext = ceil_min( datetime.datetime.now() )
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

            # heartbeat
            if status['healthcheck']:
                status['healthcheck'].heartbeat()
        except:
            # design idea to be implemented: Networking issues with data request are ok, file I/O issues should be re-raised to stop the program
            raise

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
        data_merge(cur, data_table='criticalmaps_data', stg_table=stg_table_dedupl)

        conn.commit()


def main():
    t_dl = threading.Thread(target=t_download_worker, kwargs={'stop_event':stop_event})
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

if __name__=='__main__':
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


    main()
