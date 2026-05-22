#!/usr/bin/env python3

import json
import matplotlib.pyplot as plt
import numpy as np

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

def spatial_filter_criterion(d):
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



with open('data__20260521T0041.json','r') as fin:
    data_all = json.load(fin)

data = []
for d in data_all:
    d = normalize_coords(d)
    #if spatial_filter_criterion(d):
    #    data.append(d)
    data.append(d)

longitude = [_['longitude'] for _ in data]
latitude  = [_['latitude']  for _ in data]

fig,hax = plt.subplots(1)
hax.plot(longitude, latitude, 'o')
plt.show()

X = np.vstack((np.array(longitude),np.array(latitude)))
X = np.transpose(X)
Xrad = np.radians(X)
print(X)



"""
Cluster and plot dendrogram
"""
import numpy as np
from matplotlib import pyplot as plt
from scipy.cluster.hierarchy import dendrogram

from sklearn.cluster import AgglomerativeClustering
from sklearn.datasets import load_iris

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
    rho = 6370 # radius of Earth (in spherical approximation)
    my_dist *= rho
    linkage_matrix = np.column_stack(
        [model.children_, my_dist, counts]
    ).astype(float)

    print(linkage_matrix)

    # Plot the corresponding dendrogram
    dendrogram(linkage_matrix, **kwargs)

#####
# pre-compute pair-wise distances on surface of Earth, using great circle distance
# https://scikit-learn.org/stable/modules/generated/sklearn.metrics.pairwise.haversine_distances.html
#
# -> May not be needed, because AgglomerativeClustering supports metric='haversine' out-of-the-box.
#    But keeping it because it helps to understand what the cluster algorithm did
#####
from sklearn.metrics.pairwise import haversine_distances
Xmetric = haversine_distances(Xrad)
rho = 6370 # radius of Earth (in spherical approximation)
Xmetric = rho*Xmetric
# print(Xmetric)

### TODO: understand what the default linkage 'ward' does

# setting distance_threshold=0 ensures we compute the full tree.
r_thres=100 # km
mu_thres = r_thres/rho
model = AgglomerativeClustering(metric='haversine', linkage='single', distance_threshold=mu_thres, n_clusters=None)
cluster_labels = model.fit_predict(Xrad)
print(cluster_labels)


fig,hax = plt.subplots(1)
plt.title("Hierarchical Clustering Dendrogram")
# plot the top three levels of the dendrogram
# plot_dendrogram(model, truncate_mode="level", p=3)
plot_dendrogram(model, truncate_mode="level", p=7, ax=hax)
plt.xlabel("number of points in node (or index of point if no parenthesis)")
plt.ylabel("distance [km]")
hax.set_ylim(0.1, 1.0e4)
hax.set_yscale('log')
plt.show()



# points that have no neighbor within the distance threshould count as single-element cluster with their own ID
from collections import Counter
counts_cluster_labels = Counter(cluster_labels)
counts_cluster_labels = dict(
        sorted(counts_cluster_labels.items(), key=lambda _: _[1], reverse=True)
)
print(counts_cluster_labels)


"""
Compute "Geometric median" (minimizes L1 norm in 2-D).
(Note: do this only if longitude/latitude values are from a small area, like a city.)
"""
def cluster_compute_center(id_cluster: int):
    # get all points in cluster (with hard-coded ID)
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        raise ValueError(f'no cluster with id={id_cluster}')
    points = X[idx,:]
    print(points)

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

def cluster_plot(*, hax, id_cluster: int, indicate_center=False, kwargs):
    idx = [_ for _,x in enumerate(cluster_labels) if x==id_cluster]
    if len(idx)==0:
        print(f'warning: no cluster to plot for id={id_cluster}')
    points = X[idx,:]
    hax.plot(points[:,0], points[:,1], 'o', **kwargs)
    if indicate_center:
        center = cluster_compute_center(id_cluster)
        hax.plot(center[0], center[1], '+', **kwargs)
        return center

# fixed dummy position in Hamburg for dev purposes
my_pos = [10, 53.5]

# center = cluster_compute_center(1)
# print(center)
fig,hax = plt.subplots(1)
center = cluster_plot(hax=hax,id_cluster=1, indicate_center=True, kwargs={'color':'b'})
center = cluster_plot(hax=hax,id_cluster=0, indicate_center=True, kwargs={'color':'r'})
print(center)
plt.show()
