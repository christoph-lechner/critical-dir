import pytest
import os
import psycopg
import datetime
import uuid

@pytest.fixture
def dbconn():
    """
    Example:
    Running 'pytest' with environment variable set to enable local tests
    with PostgreSQL scratch database. When using GitHub Actions, one
    could bring up a 'postgres' Docker container before launching pytest.

    $ env TESTS_PG_DSN="postgres://dev@192.168.2.253:15432/dev" pytest
    """

    # call pytest.skip here to skip these tests if DB config not provided
    if not os.getenv('TESTS_PG_DSN'):
        pytest.skip('not running tests needing DB connection, specify PostgreSQL DSN in environment variable TESTS_PG_DSN')

    ### Prepare DB ###
    # to readily see which schema is the most recent one: include UNIX epoch in schema name
    epoch = int(datetime.datetime.now().timestamp())
    my_schema = f'test_{epoch}_{uuid.uuid4().hex}'

    # Password in ~/.pgpass, line format
    # hostname:port:database:username:password
    # !mode has to be 600!
    pg_dsn = os.getenv('TESTS_PG_DSN')
    conn = psycopg.connect(pg_dsn)

    # for better test isolation, create schema with unique name
    conn.execute(f'CREATE SCHEMA {my_schema};')
    conn.execute(f'SET search_path TO {my_schema};')

    yield conn

    ### tear down ###
    # for debugging (if you want to study the outcome), don't drop the schema
    conn.execute(f'DROP SCHEMA {my_schema} CASCADE;')
    conn.commit()
    conn.close()

def test_skeleton(dbconn, capsys):
    with capsys.disabled():
        # report DB connection
        print(dbconn)
    """
    with open('doc/schema.sql','r') as fin:
        r = fin.read()
    dbconn.execute(r)
    """
