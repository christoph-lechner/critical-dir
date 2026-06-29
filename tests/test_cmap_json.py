import pytest
from critical_dir.cmaps_util import load_cmap_jsonfile
from critical_dir.cmaps_util import BadJSONDataFile
from pathlib import Path

def h_getpath(fn:str) -> Path:
    # get the path where this test script is located
    test_dir = Path(__file__).parent
    json_dir = test_dir / 'ing-test-jsons/'
    return json_dir / fn

def test_interface():
    """
    Basic interface checks
    """
    json_file1 = h_getpath('ok1.json')

    # we expect the function to return a tuple of length 2
    r_tuple = load_cmap_jsonfile(json_file1)
    assert len(r_tuple)==2
    assert isinstance(r_tuple, tuple)
    assert isinstance(r_tuple[0], list)

def test_fileload_ok():
    """
    Can we load a good file?
    """
    data,_ = load_cmap_jsonfile( h_getpath('ok1.json') )
    assert isinstance(data, list)
    assert len(data)==8

    # what happens when we load JSON file having zero device entries?
    data,_ = load_cmap_jsonfile( h_getpath('ok0.json') )
    assert len(data)==0

def test_fileload_missing_fields():
    """
    Test against files having an entry with missing field.
    Note: We don't run tests with files having extra fields!
    """
    with pytest.raises(BadJSONDataFile):
        for idtest in range(1,5):
            data,_ = load_cmap_jsonfile( h_getpath(f'bad-missing-field{idtest}.json') )

def test_fileload_check_data():
    """
    Verifies that data loaded from file matches file contents
    """
    data,_ = load_cmap_jsonfile( h_getpath('ok1.json') )
    q = data[1]
    assert q['device']=='28ef'
    assert q['latitude']==53.123456
    assert q['longitude']==10.234567
    assert q['timestamp']==1782733734
