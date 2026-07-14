#!/usr/bin/env python3

# CL, 2026-07-13

import psycopg
from psycopg.rows import dict_row
import re
import datetime
from typing import Iterator
from pydantic import BaseModel, Field


# For staging table: data schema, without fields that will be added during
# the loading process: ts_entry_creation
# In this program no hash is computed, UNIQUE_ID will be used to ensure that
# every event is only loaded one time.
# -> https://httpd.apache.org/docs/current/mod/mod_unique_id.html
datacol_ddl = \
"""
	ts TIMESTAMP WITH TIME ZONE,
	unique_id TEXT,
	time INT,
	status INT,
	response_size INT,
	method TEXT,
	path TEXT,
	protocol TEXT
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

def execute_merge(cur, *, data_table, stg_table):
    cur.execute(
        f"""
        WITH q AS(
            MERGE
            INTO
                {data_table} AS dst
            USING
                {stg_table} AS src
            ON
                dst.unique_id=src.unique_id
            WHEN MATCHED THEN DO NOTHING
            WHEN NOT MATCHED THEN
                INSERT VALUES (ts,unique_id,time,status,response_size,method,path,protocol)
            RETURNING
                -- merge_action() is new in PostgreSQL v18
                dst.unique_id, merge_action() AS action
        )
        SELECT
            COUNT(*) FILTER (WHERE action='INSERT') AS n_inserts,
            COUNT(*) FILTER (WHERE action='UPDATE') AS n_updates
        FROM q;
        """
    )
    res_m = cur.fetchone()
    return res_m


class PerformanceLogEntry(BaseModel):
    ts: datetime.datetime
    unique_id: str
    time: int
    status: int
    response_size: int = Field(ge=0)
    method: str
    path: str
    protocol: str

    @classmethod
    def from_match(cls, m: re.Match) -> "PerformanceLogEntry":
        data = m.groupdict()

        # type conversions
        data['time'] = int(data['time'])
        data['status'] = int(data['status'])
        data['response_size'] = 0 if data['response_size']=='-' else int(data['response_size'])
        data['ts'] = datetime.datetime.strptime(
            data['ts'],
            '%d/%b/%Y:%H:%M:%S %z'
        )
        return cls.model_validate(data)

def iter_log(filename: str) -> Iterator[PerformanceLogEntry]:
    # Extract information from special log format (we use 'mod_unique_id' to generate unique IDs).
    # LogFormat "%t %{UNIQUE_ID}e %D %>s %b \"%r\"" response_timing
    # -> for details, see https://httpd.apache.org/docs/2.4/mod/mod_log_config.html
    # Example line: 
    # [13/Jul/2026:14:28:01 +0000] alT18bmh4If14eX4yEg6VwAAAAQ 37836 200 - "HEAD /myapp/api/health HTTP/1.1"
    PERFORMANCE_LOG_PATTERN = re.compile(
        r'\[(?P<ts>[^\]]+)\] '
        r'(?P<unique_id>\S+) '
        r'(?P<time>\d+) '
        r'(?P<status>\d+) '
        r'(?P<response_size>\S+) ' # "-" means no bytes were sent (for instance: HEAD method)
        r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>[^"]+)"'
    )

    with open(filename) as fin:
        for lineno,line in enumerate(fin, 1):
            m = PERFORMANCE_LOG_PATTERN.match(line)
            if m is None:
                raise ValueError(f'Unable to parse line {filename}:{lineno}')
            yield PerformanceLogEntry.from_match(m)



def main():
    conn = psycopg.connect('postgres://dev@192.168.2.253:15432/dev')
    cur = conn.cursor(row_factory=dict_row)

    # create unique names for data staging step
    t0 = datetime.datetime.now()
    str_t0 = t0.strftime('%Y%m%dT%H%M%S')
    stg_table = 'stg_'+str_t0
    prepare_stg_table(cur, stg_table)

    for q in iter_log('/tmp/u/http.obj.clsrv.de.timing_log'):
        # print(q)
        cur.execute(
            f"""
            INSERT INTO {stg_table}
                (ts,unique_id, time,status,response_size, method,path,protocol)
            VALUES
                (%(ts)s,%(unique_id)s, %(time)s,%(status)s,%(response_size)s, %(method)s,%(path)s,%(protocol)s)
            """,
            q.model_dump()
        )
    res_merge = execute_merge(cur, data_table='api_perf_log', stg_table=stg_table)

    # MERGE does not perform UPDATES: "WHEN MATCHED THEN DO NOTHING"
    # so the number of updates is always zero
    print(res_merge)

    conn.commit()
    cur.close()
    conn.close()

if __name__=='__main__':
    main()
