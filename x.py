#!/usr/bin/env python3

# TODO:
# Add staging table, hash filename, line number, timestamp to ensure
# this loading process does not load the same line twice.
# Check if Apache2 can write a unique request id to the logfile (this would already solve this issue).
# -> https://httpd.apache.org/docs/current/mod/mod_unique_id.html sets UNIQUE_ID environment variable

import psycopg
from psycopg.rows import dict_row
import re
import datetime
from typing import Iterator
from pydantic import BaseModel, Field

class PerformanceLogEntry(BaseModel):
    ts: datetime.datetime
    time: int
    status: int
    response_size: int = Field(ge=0)
    method: str
    path: str
    protocol: str

    @classmethod
    def from_match(cls, m: re.Match) -> "LogEntry":
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
    # Extract information from special log format.
    # LogFormat "%t %D %>s %b \"%r\"" response_timing
    # -> for details, see https://httpd.apache.org/docs/2.4/mod/mod_log_config.html
    # Example line: 
    # [12/Jul/2026:21:24:33 +0000] 47609 200 - "HEAD /myapp/api/health HTTP/1.1"
    PERFORMANCE_LOG_PATTERN = re.compile(
        r'\[(?P<ts>[^\]]+)\] '
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

    for q in iter_log('/tmp/u/http.obj.clsrv.de.timing_log'):
        # print(q)
        cur.execute(
            """
            INSERT INTO api_perf_log
                (ts,time,status,response_size, method,path,protocol)
            VALUES
                (%(ts)s,%(time)s,%(status)s,%(response_size)s, %(method)s,%(path)s,%(protocol)s)
            """,
            q.model_dump()
        )

    conn.commit()
    cur.close()
    conn.close()

if __name__=='__main__':
    main()
