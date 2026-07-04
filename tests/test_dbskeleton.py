# 'dbconn' test fixture in conftest.py

def test_skeleton(dbconn, capsys):
    with capsys.disabled():
        # report DB connection
        print(dbconn)
