#!/usr/bin/env python3

# Comparing versions
# master d73e1f8
# cl_20260622__optim 78f3bd4
# and '395a67d' (not on a branch)

import requests
import datetime
import urllib
from deepdiff import DeepDiff

def set_t0(*, t0:datetime.datetime, baseurl:str):
    # datetime.datetime is not JSON realizable, so let's do it ourselves and format using strftime
    str_t0 = t0.strftime('%Y-%m-%dT%H:%M:%S')
    payload = {'t0':str_t0}

    url = urllib.parse.urljoin(baseurl, 'set_t0')
    r = requests.post(url, json=payload)
    r.raise_for_status()

def get_clusters(*, baseurl:str):
    url = urllib.parse.urljoin(baseurl, 'clusters')
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

base1 = 'http://localhost:8081/'
base2 = 'https://other_url/api/'

# t0 = datetime.datetime(2026,6,21, 7,00)
# t0 = datetime.datetime(2026,6,21, 9,25)
t0 = datetime.datetime(2026,6,21, 13,25)

set_t0(t0=t0, baseurl=base1)
set_t0(t0=t0, baseurl=base2)

j1 = get_clusters(baseurl=base1)
j2 = get_clusters(baseurl=base2)
diff = DeepDiff(j1,j2)
# print(diff)
if diff:
    print('results differ')
else:
    print('results in agreement')
