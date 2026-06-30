from critical_dir.cmaps_api import get_cmaps_data
from urllib.parse import urljoin
import tempfile

def test_https():
    r = get_cmaps_data(api_url='https://www.google.com/')

def test_file(tmp_path):
    fout = tmp_path / 'x.txt'
    fout.write_text('Hallo World!')
    url = urljoin('file://', str(fout))
    r = get_cmaps_data(api_url=url)
