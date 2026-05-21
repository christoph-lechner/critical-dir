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

    linkage_matrix = np.column_stack(
        [model.children_, model.distances_, counts]
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
print(Xmetric)

### TODO: understand what the default linkage 'ward' does

# setting distance_threshold=0 ensures we compute the full tree.
model = AgglomerativeClustering(metric='haversine', linkage='single', distance_threshold=0, n_clusters=None)
model = model.fit(Xrad)


fig,hax = plt.subplots(1)
plt.title("Hierarchical Clustering Dendrogram")
# plot the top three levels of the dendrogram
# plot_dendrogram(model, truncate_mode="level", p=3)
plot_dendrogram(model, truncate_mode="level", p=7, ax=hax)
plt.xlabel("Number of points in node (or index of point if no parenthesis).")
# hax.set_yscale('log')
plt.show()
