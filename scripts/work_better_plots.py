#!/usr/bin/env python3

"""
C. Lechner, 2026-06-14

Script to examine a few ways to better represent complex shapes of clusters.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pyproj import CRS, Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from k_means_constrained import KMeansConstrained
import datetime
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
        lambda q: is_in_munich(q) and is_interesting_group2(q),
        data_complete
    ))
    print(type(data))
    print(data[0])
    data_lat = [_['latitude']  for _ in data]
    data_lon = [_['longitude'] for _ in data]
    fig,hax=plt.subplots(1)
    hax.plot(data_lon,data_lat,'.')
    plt.show()

    tstart = datetime.datetime.now()

    # Define the source coordinate system (WGS84 / standard Lat-Lon)
    # and use sample point to find ideal UTM (Universal Transverse Mercator)
    # projection.
    crs_wgs84 = CRS.from_epsg(4326)
    sample_lat = data_lat[0]
    sample_lon = data_lon[0]
    utm_crs_list = query_utm_crs_info(
            datum_name='WGS 84',
            area_of_interest = AreaOfInterest(
                west_lon_degree  = sample_lon,
                south_lat_degree = sample_lat,
                east_lon_degree  = sample_lon,
                north_lat_degree = sample_lat,
            ),
    )
    utm_crs = CRS.from_epsg(utm_crs_list[0].code)

    # Transform the data to x/y
    transformer = Transformer.from_crs(crs_wgs84, utm_crs, always_xy=True)
    xs, ys = transformer.transform(data_lon, data_lat) # !order of arguments is longitude,latitude!
    xs = np.array(xs) # convert to numpy.array (we need it in this type later for the plotting)
    ys = np.array(ys)

    #fig,hax = plt.subplots(1)
    #hax.plot(xs-np.mean(xs),ys-np.mean(ys),'.')
    #hax.set_xlabel('x - <x> [m]')
    #hax.set_xlabel('y - <y> [m]')
    #plt.show()


    X = np.column_stack((xs,ys))
    total_points = len(X)
    estimated_clusters = max(1, round(total_points/4))

    # Run Constrained K-Means clustering
    # Forces every cluster to have between 3 and 5 points, leaving no outliers.
    clf = KMeansConstrained(
            n_clusters=estimated_clusters,
            size_min=3,
            size_max=5,
            random_state=42
    )
    labels = clf.fit_predict(X)

    tend = datetime.datetime.now()
    deltat = (tend-tstart).total_seconds()
    print(f'*** time needed for clustering {deltat:.3f}s ***')


    ##################################
    # Finally, let's draw some plots #
    ##################################
    def enforce_element_count(labels,curr_label):
        nele = np.sum(labels==curr_label)
        if 3<=nele and nele<=5:
            return
        raise ValueError(f'there is a cluster having {nele} elements, violating the requirements.')

    fig,hax = plt.subplots(1)
    for curr_label in set(labels):
        enforce_element_count(labels,curr_label)
        curr_x = xs[labels==curr_label]
        curr_y = ys[labels==curr_label]
        hax.plot(curr_x, curr_y, 'o')
        # Draw info rectangle indicating min/max range covered by the cluster
        # Note: not all points inside of the rect are part of the cluster!
        curr_x_min = np.min(curr_x)
        curr_x_max = np.max(curr_x)
        curr_y_min = np.min(curr_y)
        curr_y_max = np.max(curr_y)
        rect = patches.Rectangle((curr_x_min,curr_y_min), curr_x_max-curr_x_min, curr_y_max-curr_y_min, linewidth=1, edgecolor='k', facecolor='none')
        hax.add_patch(rect)
    plt.show()

if __name__=='__main__':
    main()
