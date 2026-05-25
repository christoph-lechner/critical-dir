#!/usr/bin/env python3

import time
import datetime
import signal
import threading
from threading import Event
from pathlib import Path
from cmaps_data_core import get_cmaps_data

datadir = Path('/home/cl/work/criticalmaps--richtungspfeil/cmdata/')

#####

# signal handler
done_event = Event()
stop_event = Event()
def sighandler_term(signum, frame):
    done_event.set()
    stop_event.set()

#####

def t_download_worker(*,stop_event):
    def ceil_min(dt):
        return dt.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    def wait_until(dt):
        """
        Returns True if we received a stop signal
        """
        deltat = tnext - datetime.datetime.now()
        deltat = deltat.total_seconds()
        while deltat>0:
            # break wait down into short waits to make it responsive (I think a sleep cannot be interrupted by a signal in Python)
            if deltat>3:
                deltat = 3
            # print(f'waiting for {deltat:.1f} seconds ...')
            time.sleep(deltat)
            if stop_event.is_set():
                # print('got SIGTERM/SIGINT -> stopping')
                return True
            deltat = tnext - datetime.datetime.now()
            deltat = deltat.total_seconds()
        return False


    def get_fn():
        tnow = datetime.datetime.now()
        tnowstr = tnow.strftime('%Y%m%dT%H%M%S_%f') # '%f' is always 6 digits wide and padded w/ leading zeros
        return datadir / ('data_'+tnowstr+'.json')

    # schedule first request to happen at the start of the next minute
    tnext = ceil_min( datetime.datetime.now() )
    while True:
        wait_until(tnext)
        tnext = tnext + datetime.timedelta(seconds=30)
        if stop_event.is_set():
            print('got SIGTERM/SIGINT -> stopping')
            break

        try:
            # TODO: add time outs here
            fn_out = get_fn()
            print(f'Downloading data to file {fn_out} ...')
            data = get_cmaps_data()
            with open(fn_out,'w') as fout:
                fout.write(data)
        except:
            # design idea: Networking issues with data request are ok, file I/O issues should be re-raised to stop the program
            raise


def main():
    t_dl = threading.Thread(target=t_download_worker, kwargs={'stop_event':stop_event})
    t_dl.start()

    while True:
        if done_event.is_set():
            print('main loop: got SIGTERM/SIGINT -> stopping')
            break

        # short sleeps to avoid busy waiting
        time.sleep(1)

    t_dl.join()

    return

if __name__=='__main__':
    # Install signal handlers
    # SIGTERM is handled for graceful termination
    # SIGINT  is handled for graceful termination (user pressed <Ctrl>-<C>)
    signal.signal(signal.SIGTERM, sighandler_term)
    signal.signal(signal.SIGINT,  sighandler_term)

    main()
