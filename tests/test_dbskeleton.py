import pytest
import os
import psycopg

@pytest.fixture
def dbconn():
    """
    Example:
    Running 'pytest' with environment variable set to enable local tests
    with PostgreSQL scratch database. When using GitHub Actions, one
    could bring up a 'postgres' Docker container because launching pytest.

    $ env TESTS_PG_DSN="postgres://dev@192.168.2.253:15432/dev" pytest
    """

    # call pytest.skip here to skip these tests if DB config not provided
    if not os.getenv('TESTS_PG_DSN'):
        pytest.skip('not running tests needing DB connection, specify PostgreSQL DSN in environment variable TESTS_PG_DSN')

    # Prepare DB
    pg_dsn = os.getenv('TESTS_PG_DSN')

    # Password in ~/.pgpass, line format
    # hostname:port:database:username:password
    # !mode has to be 600!
    conn = psycopg.connect(pg_dsn)
    yield conn
    conn.close()

def test_skeleton(dbconn, capsys):
    with capsys.disabled():
        # report DB connection
        print(dbconn)
    pass
