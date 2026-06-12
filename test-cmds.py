#!/usr/bin/env python3

import requests
import json

apiurl = 'http://localhost:8081/clusters'

def get_clusters(maxdist=1.0):
    p = {'maxdist':maxdist, 'exclstat':0}
    res = requests.get(apiurl, params=p)
    res.raise_for_status()
    j = res.json()
    detected_clusters = j['clusters']
    return detected_clusters

def main():
    # for these parameters, the test data returned by DataLoaderTestData
    # contains no matching clusters
    c = get_clusters(maxdist=2.0)
    print(c)
    assert len(c)==0

    # for these parameters, the test data returned by DataLoaderTestData
    # contains 1 matching clusters of size N=3
    c = get_clusters(maxdist=2.5)
    print(c)
    assert len(c)==1
    assert c[0]['N']==3

    print('checks passed -> got expected results')


if __name__=='__main__':
    main()
