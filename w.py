#!/usr/bin/env python3

import json
import matplotlib.pyplot as plt
import numpy as np
import os
import time
from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering
from collections import Counter
from pathlib import Path
from nav import get_nav


cfg = {
    'warn_file_age': 120, # seconds
    'r_thres': 100, # km, radius used for clustering (note: converted to great-circle angle using radius of Earth)
    'rho': 6371, # km, radius of Earth (in spherical approximation)
}

def normalize_coords(d):
    """
    The JSON contains the geolocation data as Int, scaled by 1E6.
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
    is_in_bbox = (9.7<=longitude) and (longitude<=10.4) and (53.35<=latitude) and (latitude<=53.75)
    return is_in_bbox

### based on code from https://scikit-learn.org/stable/auto_examples/cluster/plot_agglomerative_dendrogram.html#sphx-glr-auto-examples-cluster-plot-agglomerative-dendrogram-py
def plot_dendrogram(model, **kwargs):
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
    dendrogram(linkage_matrix, **kwargs)

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


def main(*,datafile='data.json', observer_pos, spatial_filter=None, obj_path=None, fprefix=None):
    """
    spatial_filter: function used for spatial filtering. Takes single argument (JSON data point) and returns True if point is to be retained
    """
    # fprefix should be unique to this session
    if fprefix is None:
        fprefix = 'img_123_'

    def plot_show_or_save(ftype):
        if not (obj_path and isinstance(obj_path,Path)):
            plt.show()
            return
        rel_path = (fprefix+ftype+'.png')
        absolute_path = obj_path / rel_path
        plt.savefig(absolute_path, dpi=150, bbox_inches='tight')
        # returning the relative path since the webclient sees a different path layout than the server
        return rel_path

    # Check age of data file (note: using functions returning ints to avoid loss of precision caused by floats)
    statinfo = os.stat(datafile)
    # print(statinfo.st_mtime)
    age_datafile = time.time_ns()/1000000000 - statinfo.st_mtime
    if age_datafile>cfg['warn_file_age']:
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

    fn = {}

    fig,hax = plt.subplots(1)
    hax.plot(longitude, latitude, 'o')
    fn['scatter'] = plot_show_or_save('scatter')

    X = np.vstack((np.array(longitude),np.array(latitude)))
    X = np.transpose(X)
    # print(X)


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


    fig,hax = plt.subplots(1)
    plt.title("Hierarchical Clustering Dendrogram")
    # plot the top three levels of the dendrogram
    # plot_dendrogram(model, truncate_mode="level", p=3)
    plot_dendrogram(model, truncate_mode="level", p=7, ax=hax)
    plt.xlabel("number of points in node (or index of point if no parenthesis)")
    plt.ylabel("distance [km]")
    hax.set_ylim(0.1, 1.0e4)
    hax.set_yscale('log')
    fn['dendrogram'] = plot_show_or_save('dendrogram')



    # points that have no neighbor within the distance threshould count as single-element cluster with their own ID
    counts_cluster_labels = Counter(cluster_labels)
    counts_cluster_labels = sorted(counts_cluster_labels.items(), key=lambda _: _[1], reverse=True)
    # print(counts_cluster_labels)
    sorted_cluster_ids = [
        # convert np.int64 to int
        int(_[0])
        for _ in counts_cluster_labels
    ]


    from itertools import cycle
    iter_colors = cycle(['b','r','g'])
    cluster_counter=0
    fig,hax = plt.subplots(1)
    hax.plot(observer_pos[0], observer_pos[1], 'k+')
    for id_cluster in sorted_cluster_ids:
        curr_cluster_center = cluster_plot(hax=hax,cluster_data=X,cluster_labels=cluster_labels,id_cluster=id_cluster, indicate_center=True, kwargs={'color':next(iter_colors)})
        initial_course,dist_rad = get_nav(observer_pos, curr_cluster_center)
        curr_cluster_nele = dict(counts_cluster_labels)[id_cluster]
        print(f"ID={id_cluster}: N={curr_cluster_nele}, center={curr_cluster_center}, course={initial_course} deg, dist={cfg['rho']*dist_rad} km")
        cluster_counter+=1
        if cluster_counter>=2:
            break
    hax.set_xlabel('longitude')
    hax.set_ylabel('latitude')
    fn['clusters'] = plot_show_or_save('clusters')

    return {'files':fn}


if __name__=='__main__':
    # fixed dummy position in Hamburg for dev purposes
    my_pos = np.array([10, 53.5])

    r = main(datafile='data.json', observer_pos=my_pos, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix='img_234_')
    print(r['files'])
