from critical_dir.my_util_files import parsefn
import datetime

def test_parsefn(capsys):
    ts_expected = datetime.datetime(2026,10,1,12,0,tzinfo=datetime.timezone.utc)
    q = parsefn('data_20261001T120000_1.json')
    assert q.is_valid_filename
    assert q.ts == ts_expected
    """
    with capsys.disabled():
        print(q)
        print(ts_expected)
    """
