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

@dataclass
class ClusterInfo:
    cluster_ID: int
    center: np.array
    N: int
    course: float
    dist: float
    def __str__(self):
        return f"ID={self.cluster_ID}: N={self.N}, center={self.center}, course={self.course} deg, dist={self.dist}"
    def table_header(self):
        # part of dervied dataclass to ensure that header and string representation of rows have matching layout
        return '<tr><td>(ID)</td><td>N</td><td>center</td><td>course [deg]</td><td>dist [km]</td></tr>'
    def as_html(self):
        # replace by jinja template?
        return f"<tr><td>{self.cluster_ID}</td><td>{self.N}</td><td>{self.center[0]:.2f}, {self.center[1]:.2f}</td><td>{self.course:.2f}</td><td>{self.dist:.2f}</td></tr>"


cfg = {
    'warn_file_age': 120, # seconds
    'r_thres': 100, # km, radius used for clustering (note: converted to great-circle angle using radius of Earth)
    'max_clusters': 10002,
    ### constants ###
    'rho': 6371, # km, radius of Earth (in spherical approximation)
}

def normalize_coords(d):
    """
    The JSON contains the geolocation data as Int, scaled by 1E6.
    Does not modify or remove any other fields.
    """
    def my_helper(d,key):
        if key in d:
            d[key] = d[key]/1.0e6
    my_helper(d,'longitude')
    my_helper(d,'latitude')
    return d

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
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        print(f'warning: no cluster to plot for id={id_cluster}')
    points = cluster_data[idx,:]
    hax.plot(points[:,0], points[:,1], 'o', **kwargs)
    if indicate_center:
        center = cluster_compute_center(cluster_data=cluster_data, cluster_labels=cluster_labels, id_cluster=id_cluster)
        hax.plot(center[0], center[1], '+', **kwargs)
        return center


def main(*,datafile='data.json', observer_pos, spatial_filter=None, obj_path=None, fprefix=None, exclude_isolated_points=True):
    """
    obj_path: If provided, this switches on storing images to files instead of displaying them
    spatial_filter: function used for spatial filtering. Takes single argument (JSON data point) and returns True if point is to be retained
    """

    ### HERE WE COLLECT INFOS TO BE RETURNED TO CALLER ###
    diag_info = []
    cluster_infos = []
    fn = {}

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

    def load_cmap_jsonfile(datafile, *, warn_old=True):
        # Check age of data file (note: using functions returning ints to avoid loss of precision caused by floats)
        statinfo = os.stat(datafile)
        # print(statinfo.st_mtime)
        age_datafile = time.time_ns()/1000000000 - statinfo.st_mtime
        if age_datafile>cfg['warn_file_age']:
            diag_info.append(f'WARNING: file is {age_datafile} seconds old')
            print(f'WARNING: file is {age_datafile} seconds old')

        with open(datafile,'r') as fin:
            data_all = json.load(fin)

        data = []
        for d in data_all:
            d = normalize_coords(d)
            if spatial_filter and callable(spatial_filter) and spatial_filter(d)==False:
                continue
            data.append(d)

        longitude = [_['longitude'] for _ in data]
        latitude  = [_['latitude']  for _ in data]

        fig,hax = plot_new()
        hax.plot(longitude, latitude, 'o')
        hax.set_title('Points as loaded from JSON Data')
        fn['scatter'] = plot_show_or_save(fig,'scatter')

        X = np.vstack((np.array(longitude),np.array(latitude)))
        X = np.transpose(X)
        # print(X)

        return data,X

    data,X = load_cmap_jsonfile(datafile)

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

    ### TODO: understand what the default linkage 'ward' does

    # setting distance_threshold=0 ensures we compute the full tree.
    mu_thres = cfg['r_thres']/cfg['rho']
    model = AgglomerativeClustering(metric='haversine', linkage='single', distance_threshold=mu_thres, n_clusters=None)
    cluster_labels = model.fit_predict(Xrad)
    # print(cluster_labels)


    fig,hax = plot_new()
    hax.set_title("Hierarchical Clustering Dendrogram")
    # plot the top three levels of the dendrogram
    # plot_dendrogram(hax,model, truncate_mode="level", p=3)
    plot_dendrogram(hax,model, truncate_mode="level", p=7)
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
        hax.plot(observer_pos[0], observer_pos[1], 'kx', label='your position')
        for id_cluster in sorted_cluster_ids:
            # if requested by user, ignore single-element 'clusters'
            curr_cluster_nele = dict(counts_cluster_labels)[id_cluster]
            if exclude_isolated_points and curr_cluster_nele<=1:
                continue
            #
            curr_cluster_center = cluster_plot(hax=hax,cluster_data=X,cluster_labels=cluster_labels,id_cluster=id_cluster, indicate_center=True, kwargs={'color':next(iter_colors)})
            initial_course,dist_rad = get_nav(observer_pos, curr_cluster_center)
            #
            if store_ci:
                curr_ci = ClusterInfo(cluster_ID=id_cluster, N=curr_cluster_nele, center=curr_cluster_center, course=initial_course, dist=cfg['rho']*dist_rad)
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

    return {'files':fn, 'diag_info': diag_info, 'clusters':cluster_infos}


if __name__=='__main__':
    # fixed dummy position in Hamburg for dev purposes
    my_pos = np.array([10, 53.5])

    # r = main(datafile='data.json', observer_pos=my_pos, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs'))
    r = main(datafile='data.json', observer_pos=my_pos)
