import psycopg

def get_db_conn():
    # Password in ~/.pgpass, line format
    # hostname:port:database:username:password
    # !mode has to be 600!
    conn = psycopg.connect(dbname = 'dev', 
                           user = 'dev', 
                           host= '192.168.2.253',
                           port = 15432)
    return conn
