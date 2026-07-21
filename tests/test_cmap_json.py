import pytest
from unittest.mock import Mock
from pathlib import Path
from pydantic import ValidationError
from critical_dir.cmaps_util import load_cmap_jsonfile
from critical_dir.cmaps_util import BadJSONDataFile

def h_getpath(fn:str) -> Path:
    # get the path where this test script is located
    test_dir = Path(__file__).parent
    json_dir = test_dir / 'ing-test-jsons/'
    return json_dir / fn

def test_interface():
    """
    Basic interface checks
    """
    # we expect the function to return a list
    r = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json') )
    assert isinstance(r, list)

def test_fileload_ok():
    """
    Can we load a good file?
    """
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json') )
    assert isinstance(data, list)
    assert len(data)==8

    # what happens when we load JSON file having zero device entries?
    data = load_cmap_jsonfile( h_getpath('ok0.json') )
    assert len(data)==0

def test_fileload_check_data():
    """
    Verifies that data loaded from file matches file contents
    """
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json') )
    q = data[1]
    assert q.device=='28ef'
    assert q.latitude==53.123456
    assert q.longitude==10.234567
    assert q.timestamp==1782733734

def test_cb_spatialfilter():
    """
    Verify that spatial filter callback has correct effect on returned data
    """
    def cb_f_rejectall(d):
        return False
    def cb_f_acceptall(d):
        return True

    cb_f_mock = Mock()

    # no spatial filter
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json') )
    assert len(data)==8

    # if our data has N objects, expect N calls of callback function
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json'), spatial_filter=cb_f_mock )
    assert len(data)==cb_f_mock.call_count
    # check recorded call arguments
    from unittest.mock import call
    cb_f_mock.assert_has_calls(
            [call(_) for _ in data]
    )

    # spatial filter accepting everything
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json'), spatial_filter=cb_f_acceptall )
    assert len(data)==8

    # spatial filter rejecting everything
    data = load_cmap_jsonfile( h_getpath('ok1-fixed-timestamps.json'), spatial_filter=cb_f_rejectall )
    assert len(data)==0


def test_fileload_missing_fields():
    """
    Test against files having an entry with missing field.
    Note: We don't run tests with files having extra fields!
    """
    for idtest in range(1,5):
        with pytest.raises( (BadJSONDataFile,ValidationError) ):
            data = load_cmap_jsonfile( h_getpath(f'bad-missing-field{idtest}.json') )

"""
# Test disabled because "business logic" has been moved to SQL
# -> need to add new test for this
def test_fileload_bad_latlng():
    with pytest.raises(BadJSONDataFile):
        data = load_cmap_jsonfile( h_getpath(f'bad-invalid-lat.json') )

    with pytest.raises(BadJSONDataFile):
        data = load_cmap_jsonfile( h_getpath(f'bad-invalid-lng.json') )
"""
