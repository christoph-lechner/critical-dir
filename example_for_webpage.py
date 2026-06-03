#!/usr/bin/env python3

"""
C. Lechner, 2026-06-03

Simple example for website.
"""

import datetime
from zoneinfo import ZoneInfo
from criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderDB,AlgoConfig
from db_conn import get_db_conn

def main():
    # fixed dummy position in Hamburg for dev purposes
    my_pos = [53.55, 10.0]

    # We use the "DB loader"
    dt = datetime.datetime(2026,5,29, 20,50, tzinfo=ZoneInfo('Europe/Berlin'))
    epoch = int(dt.timestamp())
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn, t0=epoch)
    my_a = MyAnalyzer(dl=my_dl)
    res = my_a.perform_analysis(
        observer_pos=my_pos,
        ag = AlgoConfig(exclude_isolated_points = True, cluster_dist_thres=0.3)
    )
    print(res)
    my_p = MyPlotter(dl=my_dl)
    my_p.doit(res=res)

if __name__=='__main__':
    main()
