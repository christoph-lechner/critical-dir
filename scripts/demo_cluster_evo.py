#!/usr/bin/env python3

"""
C. Lechner, 2026-06-03

Simple example for website.
"""

import datetime
from zoneinfo import ZoneInfo
from dataclasses import dataclass
import matplotlib.pyplot as plt
from critical_dir.criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderDB,AlgoConfig
from critical_dir.db_conn import get_db_conn
from critical_dir.exceptions import EInsufficientData, ENoData

@dataclass
class LL:
    latitude: float
    longitude: float

@dataclass(frozen=True)
class Res:
    dt: datetime.datetime
    Nclusters: int
    cluster_centers: list[LL]

def main():
    # defines when a cluster is considered as 'large'
    thres_Nlarge=3
    thres_Nlarge=2

    # To run the cluster analysis code, we need a (fixed dummy) geoposition
    # This is Hamburg, Germany
    my_pos = [53.55, 10.0]

    # define cluster algorithm parameters
    ag = AlgoConfig(exclude_isolated_points = True, cluster_dist_thres=0.3)

    # define time range to scan
    dt_end   = datetime.datetime(2026,6,8,15,0, tzinfo=ZoneInfo('Europe/Berlin'))
    dt_start = dt_end + datetime.timedelta(days=-1)

    results = []
    dt = dt_start
    while dt<=dt_end:
        # loading data from DB
        epoch = int(dt.timestamp())
        my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn, t0=epoch)
        my_a = MyAnalyzer(dl=my_dl)
        number_large_clusters=0
        curr_cc = []
        try:
            res = my_a.perform_analysis(observer_pos=my_pos, ag=ag)
            # print(res.cluster_infos)
            for ci in res.cluster_infos:
                if ci.N>=thres_Nlarge:
                    curr_cc.append(LL(ci.latitude,ci.longitude))
                    number_large_clusters += 1
        except EInsufficientData:
            # also handles case of *no* data
            # print('info: Insufficient data')
            pass
        results.append(Res(dt=dt, Nclusters=number_large_clusters, cluster_centers=curr_cc))
        dt += datetime.timedelta(minutes=15)

    # prepare data for plots
    data_dt      = [_.dt for _ in results]
    data_Nlarge  = [_.Nclusters for _ in results]
    data_cc      = [_ for r in results for _ in r.cluster_centers]
    data_cc_lat  = [_.latitude for _ in data_cc]
    data_cc_long = [_.longitude for _ in data_cc]

    # produce plots
    fig,axs = plt.subplots(2)
    hax = axs[0]
    hax.plot(data_dt, data_Nlarge, 'k')
    hax.set_xlabel('timestamp')
    hax.set_ylabel(f'number of clusters with at least {thres_Nlarge} members')
    hax = axs[1]
    hax.plot(data_cc_long, data_cc_lat, 'k.')
    hax.set_xlabel('longitude of cluster center')
    hax.set_xlabel('latitude of cluster center')
    plt.show()

if __name__=='__main__':
    main()
