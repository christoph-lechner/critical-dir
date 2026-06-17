#!/usr/bin/env python3

import threading
import queue
import requests
import datetime
import time
import pandas as pd

def req_worker(q, worker_id, URL = 'http://localhost:8081/clusters'):
    def wait_until(dt):
        deltat = tnext - datetime.datetime.now()
        deltat = deltat.total_seconds()
        while deltat>0:
            time.sleep(deltat)
            deltat = tnext - datetime.datetime.now()
            deltat = deltat.total_seconds()
        return

    tnext = datetime.datetime.now()
    for jj in range(0,5):
        wait_until(tnext)
        # print('sending req')

        # send HTTP request and measure total time needed
        tstart = datetime.datetime.now()
        res = requests.get(URL)
        res.raise_for_status()
        tend = datetime.datetime.now()
        deltat = (tend-tstart).total_seconds()
        q.put({'worker_id': worker_id, 'deltat':deltat})

        tnext += datetime.timedelta(seconds=10)

def main():
    q = queue.Queue()

    nthreads = 3

    ### generate threads and then start them ###
    threads = []
    for worker_id in range(0,nthreads):
        threads.append(
            threading.Thread(target=req_worker, args=(q,worker_id,))
        )
    for currt in threads:
        currt.start()

    ### wait for threads to finish ###
    for currt in threads:
        currt.join()

    # drain queue with results
    lres = []
    try:
        while True:
            lres.append(q.get_nowait())
    except queue.Empty:
        pass # we expect getting this Exception once queue is empty

    df = pd.DataFrame(lres)
    stats = df.groupby('worker_id')['deltat'].agg(
                count='count',mean='mean',std='std',minimum='min',maximum='max'
            )
    print(stats)

if __name__=='__main__':
    main()
