#!/usr/bin/env python3

# reuses code from wiki proj., remove_old_streamdumps.py, commit id 6c05767 (Jan 11, 2026)

import os
import re
from dataclasses import dataclass
import datetime
from pathlib import Path
from critical_dir.settings import get_settings

@dataclass
class FileInfo:
    is_valid_filename: bool = False
    fn: str = None
    ts: datetime.datetime = None

def parsefn(fn):
    m = re.match(r'^data_([0-9]{8}T[0-9]{6})_[0-9]+.json$', fn)
    if m:
        ts_str = m.group(1) # first parenthesized subgroup
        # print(f'match: {ts_str}')

        # In Python 3.11 (and later), datetime.datetime.fromisoformat can parse most ISO8601 formats (such as "20251127T210500" used here)
        # ts = datetime.datetime.fromisoformat(ts_str)
        # For Python 3.10, a different solution is needed
        ts = datetime.datetime.strptime(ts_str, '%Y%m%dT%H%M%S')
        return FileInfo(is_valid_filename=True,fn=fn,ts=ts)
    return FileInfo(is_valid_filename=False,fn=fn)

def get_list_of_files(datadir):
    lof = []
    for fn_ in os.listdir(datadir):
        curr_fileinfo = parsefn(fn_)
        if curr_fileinfo.is_valid_filename:
            lof.append(curr_fileinfo)
    return(lof)

def identify_most_recent_file(datadir, *, n=1):
    """
    'n': number of files to return. Function may also return less, for instance if there are not enough files in the directory
    """
    if n<1:
        raise ValueError('number of files to return must be positive')

    lof = get_list_of_files(datadir)
    # empty directory? -> return None
    if len(lof)==0:
        return None

    lof = sorted(lof, key=lambda _: _.ts, reverse=True)
    if n>1:
        return lof[:n]

    return lof[0]

def main():
    settings = get_settings()
    datadir = Path(settings.api_downloader_json_outdir)
    print(identify_most_recent_file(datadir, n=2))

if __name__=='__main__':
    main()
