#!/usr/bin/env python3

import requests
import json
import os
from urllib.parse import urljoin
import datetime

def get_api_baseurl():
    """
    Helper function for testing API server.
    """
    # default value
    apiurl = 'http://localhost:8081/'
    if 'TEST_APIURL' in os.environ:
        apiurl = os.environ['TEST_APIURL']
    return apiurl

def get_api_baseurl_auth():
    """
    Helper function for testing API server.
    """
    # default value
    apiurl = 'http://localhost:8082/'
    if 'TEST_APIURL_AUTH' in os.environ:
        apiurl = os.environ['TEST_APIURL_AUTH']
    return apiurl


def get_clusters(maxdist=1.0):
    apiurl = urljoin(get_api_baseurl(), '/clusters')
    p = {'maxdist':maxdist, 'exclstat':0} # the API server ignores these parameters when it is not run in test mode

    res = requests.get(apiurl, params=p)
    res.raise_for_status()
    j = res.json()
    detected_clusters = j['clusters']
    return detected_clusters

def test_api_clusters():
    """
    These tests assume that the postgres DB contains the dataset returned
    by DataLoaderTestData, with current timestamp. This data is prepared
    in the test environment by the SQL start-up scripts invoked when running
    the "postgres" Docker container.
    """

    # for these parameters, the test data returned by DataLoaderTestData
    # contains no matching clusters
    c = get_clusters(maxdist=2.0)
    print(c)
    assert len(c)==0

    def q():
        # for these parameters, the test data returned by DataLoaderTestData
        # contains 1 matching clusters of size N=3
        c = get_clusters(maxdist=2.5)
        print(c)
        assert len(c)==1
        assert c[0]['N']==3

    # running this test twice to check if correct data is retrieved from cache
    q()
    q()

    print('checks passed -> got expected results')

def test_api_checks():
    """
    Test other API endpoints that should be present.
    The test checks that a HTTP status code indicating success is returned, it does not inspect the result.
    """
    def doit(endpoint:str, *, method='get'):
        apiurl = urljoin(get_api_baseurl(), endpoint)
        if method=='get':
            res = requests.get(apiurl)
        elif method=='head':
            res = requests.head(apiurl)
        else:
            raise ValueError('unknown method')
        res.raise_for_status()

    doit('/clusters')
    doit('/clusters_demo')
    doit('/health_no_freshness_check')
    doit('/health_no_freshness_check', method='head')
    # here the outcome can depend on the freshness of the DB (OK because for the test of Docker image, the timestamps in test db are set to current time)
    doit('/health')
    doit('/health', method='head')
    # 2026-06-16: not checking: /location, /location_demo, /inspect -> considering to remove these

def test_api_checks_t0():
    ### First test: server without configured credentials -> has to return HTTP 401 ###
    apiurl = urljoin(get_api_baseurl(), '/set_t0')
    r = requests.post(apiurl)
    # in the request no credentials were sent -> check that server sent HTTP status 401
    assert r.status_code==401

    ### Second test: server with configured credentials -> has to return HTTP 401 ###
    apiurl = urljoin(get_api_baseurl_auth(), '/set_t0')
    r = requests.post(apiurl)
    # in the request no credentials were sent -> check that server sent HTTP status 401
    assert r.status_code==401

    ### Third test: server with configured credentials, test what happens with wrong credentials ###
    cred = requests.auth.HTTPBasicAuth('user','badpassword')
    apiurl = urljoin(get_api_baseurl_auth(), '/set_t0')
    r = requests.post(apiurl, auth=cred)
    # in the request wrong credentials were sent -> check that server sent HTTP status 401
    assert r.status_code==401

    ### Forth test: server with configured credentials, send correct request (including correct credentials) ###
    # from "movie maker": datetime.datetime is not JSON realizable, so let's do it ourselves and format using strftime
    t0 = datetime.datetime.now()
    str_t0 = t0.strftime('%Y-%m-%dT%H:%M:%S')
    payload = {'t0':str_t0}

    cred = requests.auth.HTTPBasicAuth('johndoe','pwd')
    apiurl = urljoin(get_api_baseurl_auth(), '/set_t0')
    r = requests.post(apiurl, json=payload, auth=cred)
    r.raise_for_status()
    assert r.status_code==200

