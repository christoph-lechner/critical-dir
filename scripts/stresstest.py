#!/usr/bin/env python3

import threading
import queue
import requests
import datetime
import time
import pandas as pd

def clock_worker(*, qstop, tstart, URL = 'http://localhost:8081/set_t0'):
    """
    qstop: Put something into this queue (not important what), for this thread to stop
    """
    t_loop_start = datetime.datetime.now()
    while qstop.empty():
        tnow = datetime.datetime.now()
        time_elapsed = tnow - t_loop_start
        t0 = tstart + time_elapsed
        print(f'tnow={tnow} (deltat={time_elapsed.total_seconds()}): setting API server time to: {t0}')

        # datetime.datetime is not JSON realizable, so let's do it ourselves and format using strftime
        str_t0 = t0.strftime('%Y-%m-%dT%H:%M:%S')
        payload = {'t0':str_t0}
        r = requests.post(URL, json=payload)
        r.raise_for_status()
        time.sleep(5)
    print('*** clock thread: exit ***')


def req_worker(*, q, qstop, worker_id, trep=5, URL = 'http://localhost:8081/clusters'):
    """
    qstop: Put something into this queue (not important what), for this thread to stop
    """
    def wait_until(dt):
        deltat = tnext - datetime.datetime.now()
        deltat = deltat.total_seconds()
        while deltat>0:
            time.sleep(deltat)
            deltat = tnext - datetime.datetime.now()
            deltat = deltat.total_seconds()
        return

    tnext = datetime.datetime.now()
    while qstop.empty():
        wait_until(tnext)
        # print('sending req')

        # send HTTP request and measure total time needed
        tstart = datetime.datetime.now()
        res = requests.get(URL)
        res.raise_for_status()
        tend = datetime.datetime.now()
        deltat = (tend-tstart).total_seconds()
        q.put({'worker_id': worker_id, 'deltat':deltat})
        tnext += datetime.timedelta(seconds=trep)

    print(f'*** load thread {worker_id}: exit ***')

def main():
    q_res = queue.Queue()
    nthreads = 10

    # To ensure that benchmarking results are not skewed by the cache, we have to start with empty cache or with a time range that was not covered before
    t_clock_start = datetime.datetime(2026,6,21, 14,20)

    ### generate clock thread and start it ###
    q_clock_stop = queue.Queue()
    args_clock = {'qstop':q_clock_stop, 'tstart':t_clock_start}
    clock_thread = threading.Thread(target=clock_worker, kwargs=args_clock)
    clock_thread.start()
    time.sleep(1) # to be sure that the time is right when the requests are sent


    ### generate requestor threads and then start them ###
    q_stop = queue.Queue()
    threads = []
    for worker_id in range(0,nthreads):
        # slightly different repetition times, so after a short time all threads request at completely different times
        my_trep = 5+0.05*worker_id
        print(f'{my_trep}')
        args = {'q':q_res, 'qstop':q_stop, 'worker_id':worker_id, 'trep':my_trep}
        threads.append(
            threading.Thread(target=req_worker, kwargs=args)
        )
    for currt in threads:
        currt.start()

    ### wait while the threads acquire data ###
    time.sleep(30*60)

    ### send stop signal ###
    for _ in range(nthreads):
        q_stop.put({})

    ### wait for threads to finish ###
    for currt in threads:
        currt.join()
    # after all workers are done, stop time-adjustment thread
    q_clock_stop.put({})
    clock_thread.join()

    # drain queue with results
    lres = []
    try:
        while True:
            lres.append(q_res.get_nowait())
    except queue.Empty:
        pass # we expect getting this Exception once queue is empty

    df = pd.DataFrame(lres)
    stats = df.groupby('worker_id')['deltat'].agg(
                count='count',
                median='median',
                p90=lambda x: x.quantile(0.90),
                p95=lambda x: x.quantile(0.95),
                mean='mean', std='std', minimum='min', maximum='max',
            )
    print(stats)

if __name__=='__main__':
    main()
