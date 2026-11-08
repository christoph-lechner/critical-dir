from critical_dir.my_util_files import parsefn,get_fn
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

def test_getfn_canrun(tmpdir):
    fn = get_fn(outdir=tmpdir)

    # see that we can actually create the file (this tests that the directory exists, including the per-day subdirectory)
    with open(fn,'w') as fout:
        pass

def test_get_parse(tmpdir,capsys):
    """
    Test functions used to work with filenames having timestamps:
    create timestamp -> create filename (as string) -> extract timestamp from filename -> compare with original timestamp
    """
    # generate timestamp for the test
    ts = datetime.datetime.now(tz=datetime.timezone.utc)
    ts = ts.replace(microsecond=0) # the parsing function does not return fraction of a second
    # only for the test, we provide the timestamp to the function
    fn = get_fn(outdir=tmpdir, test_ts=ts, just_filename=True)
    parsed = parsefn(fn)
    """
    with capsys.disabled():
        print(ts)
        print(fn)
        print(parsed)
    """
    assert parsed.is_valid_filename
    assert parsed.ts == ts

