import psycopg
from .settings import settings

def get_db_conn():
    # Configure DSN via environment variable (see file ".env")
    #
    # Password in ~/.pgpass, line format
    # hostname:port:database:username:password
    # !mode has to be 600!
    conn = psycopg.connect(str(settings.pg_dsn))
    return conn
