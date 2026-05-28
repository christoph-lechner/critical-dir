#!/usr/bin/env python3

# Test connection to postgreSQL database

# If needed adjust connection parameters in this function:
from db_conn import get_db_conn

def testconn():
    print('Connecting to DB ...')
    conn = get_db_conn()
    print('Success: Connection to DB established')

    # https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories
    from psycopg.rows import dict_row
    cur = conn.cursor(row_factory=dict_row)

    cur.execute('SELECT (1+1);')

    cur.close()
    conn.close()

    print('*** Connection Test successful ***')

if __name__=='__main__':
    testconn()
