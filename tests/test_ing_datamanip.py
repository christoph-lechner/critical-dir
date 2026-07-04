# 'dbconn' test fixture in conftest.py

def test_skeleton(dbconn, capsys):
    # prepare DB structure
    with open('doc/schema.sql','r') as fin:
        r = fin.read()
    dbconn.execute(r)
