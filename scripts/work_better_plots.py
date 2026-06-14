#!/usr/bin/env python3

"""
C. Lechner, 2026-06-14

Script to examine a few ways to better represent complex shapes of clusters.
"""

"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pyproj import CRS, Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from k_means_constrained import KMeansConstrained
"""
import datetime
from critical_dir.wip_subclusters import generate_subclusters
from zoneinfo import ZoneInfo
from critical_dir.criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderDB,AlgoConfig
from critical_dir.db_conn import get_db_conn

def main():
    # fixed dummy position in Hamburg for dev purposes
    my_pos = [53.55, 10.0]

    # We use the "DB loader"
    dt = datetime.datetime(2026,6,14, 15,00, tzinfo=ZoneInfo('Europe/Berlin')) # "Sternfahrt" in Munich, Germany
    epoch = int(dt.timestamp())
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn, t0=epoch)
    data_complete = my_dl.get_data()


    def is_in_munich(q):
        lat0 = 48.13
        lon0 = 11.57
        if abs(q['latitude']-lat0)<0.5 and abs(q['longitude']-lon0)<0.5:
            return True
        return False
    #
    # Helper functions to select interesting point groups.
    # Needed because no clustering algorithm has been applied (we use the
    # data "directly from the source") and thus outliers are to be expected.
    def is_interesting_group1(q):
        if 48.11<=q['latitude'] and q['latitude']<=48.12:
            return True
        return False
    def is_interesting_group2(q):
        if 48.146<=q['latitude'] and q['latitude']<=48.172 and 11.53<=q['longitude'] and q['longitude']<=11.56:
            return True
        return False
    data = list(filter(
        lambda q: is_in_munich(q), # and is_interesting_group2(q),
        data_complete
    ))
    #print(type(data))
    #print(data[0])
    generate_subclusters(data=data, do_plot=True)

if __name__=='__main__':
    main()
