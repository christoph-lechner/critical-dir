#!/usr/bin/env python3

# for FastAPI servers use at least backend 'Agg' (! matplotlib.pyplot is not thread-safe, see https://matplotlib.org/stable/users/faq.html#work-with-threads !)
# ... and don't use 'plt'.
#import matplotlib
#matplotlib.use('Agg')
from matplotlib.figure import Figure

# but we still have to define the symbol 'plt' because of the code for interactive operation
import matplotlib.pyplot as plt

import json
import numpy as np
import os
import time
from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering
from collections import Counter
from pathlib import Path
from dataclasses import dataclass
import geopandas as gpd
from nav import get_nav
from my_util_files import get_list_of_files
from cmaps_util import load_cmap_jsonfile
import psycopg
from psycopg.rows import dict_row
from db_conn import get_db_conn


@dataclass
class ClusterInfo:
    cluster_ID: int
    latitude: float
    longitude: float
    N: int
    course: float
    dist: float
    def __str__(self):
        return f"ID={self.cluster_ID}: N={self.N}, center={self.latitude}, {self.longitude}, course={self.course} deg, dist={self.dist}"
    def table_header(self):
        # part of dervied dataclass to ensure that header and string representation of rows have matching layout
        return '<tr><td>(ID)</td><td>N</td><td>center</td><td>course [deg]</td><td>dist [km]</td></tr>'
    def as_html(self):
        # replace by jinja template?
        return f"<tr><td>{self.cluster_ID}</td><td>{self.N}</td><td>{self.latitude:.2f}, {self.longitude:.2f}</td><td>{self.course:.2f}</td><td>{self.dist:.2f}</td></tr>"


cfg = {
    'warn_file_age': 120, # seconds
    'r_thres': 2, # km, radius used for clustering (note: converted to great-circle angle using radius of Earth)

    'max_clusters': 1000,
    ### constants ###
    'rho': 6371, # km, radius of Earth (in spherical approximation)
}

def spatial_filter_HH(d):
    """
    Returns False if spatial filter criterion is not met OR if coordinate data is missing
    """
    longitude = d.get('longitude')
    latitude  = d.get('latitude')
    # essential fields missing -> drop this datapoint
    if longitude is None or latitude is None:
        return False
    
    # check against rect containing the State of Hamburg
    is_in_bbox = (9.7<=longitude) and (longitude<=10.35) and (53.35<=latitude) and (latitude<=53.75)
    return is_in_bbox

### based on code from https://scikit-learn.org/stable/auto_examples/cluster/plot_agglomerative_dendrogram.html#sphx-glr-auto-examples-cluster-plot-agglomerative-dendrogram-py
def plot_dendrogram(hax, model, **kwargs):
    # Create linkage matrix and then plot the dendrogram

    # create the counts of samples under each node
    counts = np.zeros(model.children_.shape[0])
    n_samples = len(model.labels_)
    for i, merge in enumerate(model.children_):
        current_count = 0
        for child_idx in merge:
            if child_idx < n_samples:
                current_count += 1  # leaf node
            else:
                current_count += counts[child_idx - n_samples]
        counts[i] = current_count

    # Using 'haversine' metric, distances are in radians
    # -> convert to km.
    my_dist = model.distances_
    print(my_dist)
    my_dist *= cfg['rho']
    linkage_matrix = np.column_stack(
        [model.children_, my_dist, counts]
    ).astype(float)
    # print(linkage_matrix)

    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, ax=hax, **kwargs)

def cluster_compute_center(*, cluster_data, cluster_labels, id_cluster: int):
    """
    Compute "Geometric median" (minimizes L1 norm in 2-D).
    (Note: do this only if longitude/latitude values are from a small area, like a city.)
    """
    # get all points in cluster (with hard-coded ID)
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        raise ValueError(f'no cluster with id={id_cluster}')
    points = cluster_data[idx,:]
    # print(points)

    from scipy.optimize import minimize

    def total_distance(center, points):
        return np.sum(np.linalg.norm(points - center, axis=1))

    initial_guess = points.mean(axis=0)

    result = minimize(
        total_distance,
        initial_guess,
        args=(points,)
    )
    return result.x

def plot_city(hax):
    """
    Helper function to plot geographical information such as city limits
    """
    gdf = gpd.read_file('mapdata/Hamburg_Stadtteilestatistik.shp')
    print(gdf.crs) # info from .prj file

    # Note: could add map using contextily, here we do need Web Mercator (EPSG:3857)
    # list of EPSG codes https://en.wikipedia.org/wiki/EPSG_Geodetic_Parameter_Dataset
    gdf = gdf.to_crs(epsg=4326) # latitude/longitude
    gdf.plot(ax=hax, color='white', edgecolor='grey')


def cluster_plot(*, hax, cluster_data, cluster_labels, id_cluster: int, indicate_center=False, kwargs):
    """
    cluster_data: just the coordinate matrix, holding longitude and latitude for all data points
    """
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        print(f'warning: no cluster to plot for id={id_cluster}')
    points = cluster_data[idx,:]
    hax.plot(points[:,1], points[:,0], 'o', **kwargs)
    if indicate_center:
        center = cluster_compute_center(cluster_data=cluster_data, cluster_labels=cluster_labels, id_cluster=id_cluster)
        hax.plot(center[1], center[0], '+', **kwargs)
        return [center[0],center[1]]

def plot_device_trace(*, cur, hax, deviceid, timestamp_min, timestamp_max=None, kwargs={}):
    """
    timestamp_min: only consider points after this Unix epoch value
    timestamp_max: planned feature: to be able to specify a time range to be considered for plotting
    kwargs: additional args to be passed to 'plot' function call
    """
    if timestamp_max:
        raise ValueError('--- not implemented yet ---')

    cur.execute(
        """
        SELECT longitude,latitude FROM criticalmaps_data WHERE deviceid=%s AND timestamp>=%s ORDER BY timestamp DESC;
        """,
        (deviceid,timestamp_min)
    )
    res_rows = cur.fetchall()
    if len(res_rows)<1:
        print(f'Warning: deviceid={curr_devid}: insufficient data for trace plot')
        return len(res_rows)

    longitude = [_['longitude'] for _ in res_rows]
    latitude  = [_['latitude']  for _ in res_rows]
    hax.plot(longitude, latitude, '-', **kwargs)
    return len(res_rows)

def cluster_plot_persistence(*, hax, cluster_complete_data, cluster_labels, id_cluster: int, trace_persistence=900, kwargs):
    """
    cluster_complete_data: expects list of dicts, as loaded from single JSON file
    trace_persistence: persistence of trace, in seconds
    """
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        print(f'warning: no cluster to plot for id={id_cluster}')
        return # nothing to do

    # establish DB connection
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    conn = get_db_conn()
    cur = conn.cursor(row_factory=dict_row)

    # iterate over device IDs for all points in this cluster
    for p in idx:
        curr_devid = cluster_complete_data[p]['device']
        timecutoff_epoch = time.time() - trace_persistence
        plot_device_trace(cur=cur, hax=hax, deviceid=curr_devid, timestamp_min=timecutoff_epoch, kwargs=kwargs)
        

def main(*,datafile=None, observer_pos, spatial_filter=None, obj_path=None, fprefix=None, exclude_isolated_points=True, cluster_dist_thres=None, cluster_trace_persistence=900):
    """
    obj_path: If provided, this switches on storing images to files instead of displaying them
    spatial_filter: function used for spatial filtering. Takes single argument (JSON data point) and returns True if point is to be retained
    """

    ### HERE WE COLLECT INFOS TO BE RETURNED TO CALLER (= the client via the API server) ###
    diag_info = []
    cluster_infos = []
    fn = {}

    # caller can override value of distance threshold for clustering process
    if cluster_dist_thres:
        cfg['r_thres'] = cluster_dist_thres

    # fprefix should be unique to this session
    if fprefix is None:
        fprefix = 'img_123_'

    def plot_new():
        if not obj_path:
            fig,hax = plt.subplots(1)
        else:
            fig = Figure()
            hax = fig.add_subplot(111)
        return fig,hax

    def plot_show_or_save(fig, ftype):
        if not (obj_path and isinstance(obj_path,Path)):
            plt.show()
            return
        rel_path = (fprefix+ftype+'.png')
        absolute_path = obj_path / rel_path
        fig.savefig(absolute_path, dpi=150, bbox_inches='tight')
        plt.close(fig) # frees resources
        # returning the relative path since the webclient sees a different path layout than the server
        return rel_path

    def cb_age(age):
        if age>cfg['warn_file_age']:
            diag_info.append(f'WARNING: file is {age} seconds old')
            print(f'WARNING: file is {age} seconds old')


    def load_from_DB():
        """
        First implementation to retrieve most recent coordinates seen for every device.
        Uses temporal cut-off. If cut-off time is different from that used by API server (sending JSON data files), the data points in the dataset will be different as well -- for instance if a mobile device starts/ceases sending data.
        Currently emulates data structure returned by JSON loading function.
        """
        # establish DB connection
        # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
        conn = get_db_conn()
        cur = conn.cursor(row_factory=dict_row)

        cur.execute(
            """
            WITH qq AS (
                WITH q_ts_mostrecent AS (
                    SELECT MAX(timestamp) AS timestamp_mostrecent FROM criticalmaps_data
                )
                SELECT
                    c.deviceid,c.longitude,c.latitude,c.timestamp, ROW_NUMBER() OVER (PARTITION BY c.deviceid ORDER BY c.timestamp DESC) AS rn
                FROM criticalmaps_data AS c, q_ts_mostrecent
                WHERE timestamp>=q_ts_mostrecent.timestamp_mostrecent-150
            )
            SELECT deviceid AS device, longitude, latitude, timestamp FROM qq WHERE rn=1;
            """
        )
        res_rows = cur.fetchall()
        longitude = [_['longitude'] for _ in res_rows]
        latitude  = [_['latitude']  for _ in res_rows]
        X = np.vstack((np.array(latitude),np.array(longitude)))
        X = np.transpose(X)
        data = res_rows
        return data,X
    
    if datafile:
        data,X = load_cmap_jsonfile(datafile, spatial_filter=spatial_filter, cb_diag_file_age=cb_age)
    else:
        print('loading current positions from DB')
        data,X = load_from_DB()

    """
    Cluster and plot dendrogram
    """
    #####
    # pre-compute pair-wise distances on surface of Earth, using great circle distance
    # https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html
    #
    # -> May not be needed, because AgglomerativeClustering supports metric='haversine' out-of-the-box.
    #    But keeping it because it helps to understand what the cluster algorithm did
    #####
    # for the clustering algorithm, we need long/lat in radians
    Xrad = np.radians(X)

    from sklearn.metrics.pairwise import haversine_distances
    Xmetric = haversine_distances(Xrad)
    Xmetric = cfg['rho']*Xmetric
    # print(Xmetric)
    # print(X)

    ### TODO: understand what the default linkage 'ward' does

    # setting distance_threshold=0 ensures we compute the full tree.
    mu_thres = cfg['r_thres']/cfg['rho']
    model = AgglomerativeClustering(metric='haversine', linkage='single', distance_threshold=mu_thres, n_clusters=None)
    cluster_labels = model.fit_predict(Xrad)
    # print(cluster_labels)


    fig,hax = plot_new()
    hax.set_title("Hierarchical Clustering Dendrogram")
    # plot the top three levels of the dendrogram
    plot_dendrogram(hax, model, truncate_mode="level", p=7, color_threshold=cfg['r_thres'])
    hax.set_xlabel("number of points in node (or index of point if no parenthesis)")
    hax.set_ylabel("distance [km]")
    hax.set_ylim(0.1, 3.5*cfg['rho']) # maximum length of great circle is pi*radius
    hax.set_yscale('log')
    fn['dendrogram'] = plot_show_or_save(fig, 'dendrogram')



    # points that have no neighbor within the distance threshould count as single-element cluster with their own ID
    counts_cluster_labels = Counter(cluster_labels)
    counts_cluster_labels = sorted(counts_cluster_labels.items(), key=lambda _: _[1], reverse=True)
    # print(counts_cluster_labels)
    sorted_cluster_ids = [
        # convert np.int64 to int
        int(_[0])
        for _ in counts_cluster_labels
    ]

    def geoplot_cluster_analysis(*, only_local=False, store_ci=True):
        from itertools import cycle
        iter_colors = cycle(['b','r','g'])
        cluster_counter=0

        fig,hax = plot_new()
        if only_local:
            plot_city(hax)
        hax.plot(observer_pos[1], observer_pos[0], 'kx', label='your position')
        for id_cluster in sorted_cluster_ids:
            # if requested by user, ignore single-element 'clusters'
            curr_cluster_nele = dict(counts_cluster_labels)[id_cluster]
            if exclude_isolated_points and curr_cluster_nele<=1:
                continue
            #
            # for correct z stacking: plot persistence traces first (would be better to plot *all* persistence traces first, then all current positions)
            curr_color = next(iter_colors)
            cluster_plot_persistence(hax=hax, cluster_complete_data=data, cluster_labels=cluster_labels, id_cluster=id_cluster, trace_persistence=cluster_trace_persistence, kwargs={'color':curr_color, 'alpha':0.5})
            curr_cluster_center = cluster_plot(hax=hax,cluster_data=X,cluster_labels=cluster_labels,id_cluster=id_cluster, indicate_center=True, kwargs={'color':curr_color})
            initial_course,dist_rad = get_nav(observer_pos, curr_cluster_center)
            #
            if store_ci:
                curr_ci = ClusterInfo(cluster_ID=id_cluster, N=curr_cluster_nele, latitude=curr_cluster_center[0], longitude=curr_cluster_center[1], course=initial_course, dist=cfg['rho']*dist_rad)
                cluster_infos.append(curr_ci)
                print(curr_ci)
            #
            cluster_counter+=1
            if cluster_counter>=cfg['max_clusters']:
                break
        hax.set_xlabel('longitude')
        hax.set_ylabel('latitude')
        hax.set_title('Result of Clustering Analysis')
        if only_local:
            hax.set_xlim(9.7, 10.35)
            hax.set_ylim(53.35, 53.75)
        fig.legend()
        #
        my_file_key = 'clusters'
        if only_local:
            my_file_key = 'clusters_local'
        fn[my_file_key] = plot_show_or_save(fig, my_file_key)

    geoplot_cluster_analysis(only_local=False)
    geoplot_cluster_analysis(only_local=True, store_ci=False)

    return {'files':fn, 'diag_info':diag_info, 'clusters':cluster_infos}


if __name__=='__main__':
    # fixed dummy position in Hamburg for dev purposes
    my_pos = np.array([53.55, 10.0])

    # r = main(datafile='data.json', observer_pos=my_pos, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs'))
    # r = main(datafile='cmdata/data_20260526T220330_002729.json', observer_pos=my_pos, exclude_isolated_points=False)
    r = main(observer_pos=my_pos, exclude_isolated_points=False)
