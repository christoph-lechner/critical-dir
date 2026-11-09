"""
Plotting code from criticaldir_core.py that is currently not being used.

CL, 2026-Nov-02
"""

import matplotlib
# for FastAPI servers use at least backend 'Agg' (! matplotlib.pyplot is not thread-safe, see https://matplotlib.org/stable/users/faq.html#work-with-threads !)
# ... and don't use 'plt'.
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
from sklearn.metrics.pairwise import haversine_distances
from collections import Counter
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
import geopandas as gpd
from functools import partial
from .nav import get_nav
from .my_util_files import get_list_of_files
from .cmaps_util import load_cmap_jsonfile
from .exceptions import EInsufficientData, ENoData
import psycopg
from psycopg.rows import dict_row
import datetime
from itertools import cycle
from .db_conn import get_db_conn


class MyPlotter:
    def __init__(self, *, dl: DataLoader, obj_path=None, fprefix=None):
        """
        dl: Instance of DataLoader-derived class. Contains code for loading data. Currently it is also needed for the plotter, because some plots may need additional data from the DB
        obj_path: If provided, this switches on storing images to files instead of displaying them
        """
        if not isinstance(dl, DataLoader):
            raise ValueError('expecting DataLoader object')

        # fprefix should be unique to this session
        if fprefix is None:
            fprefix = 'img_123_'

        self.reset_status()

        self.store_plots=False
        if obj_path and isinstance(obj_path,Path):
            self.store_plots=True

        self.fprefix = fprefix
        self.obj_path = obj_path
        self.dl = dl


    def reset_status(self):
        ### HERE WE COLLECT INFOS TO BE RETURNED TO CALLER (= the client via the API server) ###
        self.diag_info = []
        self.cluster_infos = []
        self.fn = {}

    ### HELPER FUNCTIONS FOR PLOT CREATION/STORAGE ###
    def plot_new(self, subplot_kwargs={}):
        # Remark: plt.subplots and fig.add_subplot use different parameter to pass on kwargs for subplot
        # (initially this was implemented to generate polar plot)
        if not self.store_plots:
            fig,hax = plt.subplots(1, subplot_kw=subplot_kwargs)
        else:
            fig = Figure()
            hax = fig.add_subplot(111, **subplot_kwargs)
        return fig,hax

    def plot_show_or_save(self, fig, ftype):
        if not self.store_plots:
            plt.show()
            return
        rel_path = (self.fprefix+ftype+'.png')
        absolute_path = self.obj_path / rel_path
        fig.savefig(absolute_path, dpi=150, bbox_inches='tight')
        plt.close(fig) # frees resources
        # returning the relative path since the webclient sees a different path layout than the server
        return rel_path

    def cluster_plot(self, *, hax, cluster_data, cluster_labels, id_cluster: int, indicate_center=False, kwargs):
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

    def plot_device_trace(self, *, cur, hax, deviceid, timestamp_min, timestamp_max=None, kwargs={}):
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

    def cluster_plot_persistence(self, *, hax, cluster_complete_data, cluster_labels, id_cluster: int, trace_persistence=900, kwargs):
        """
        cluster_complete_data: expects list of dicts, as loaded from single JSON file
        trace_persistence: persistence of trace, in seconds
        """
        # FIXME: 2026-06-02: name of argument 'cluster_complete_data' is misleading
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
            self.plot_device_trace(cur=cur, hax=hax, deviceid=curr_devid, timestamp_min=timecutoff_epoch, kwargs=kwargs)

    def plot_dendrogram(self, hax, model, **kwargs):
        """
        Create linkage matrix and then plot the dendrogram

        based on code from https://scikit-learn.org/stable/auto_examples/cluster/plot_agglomerative_dendrogram.html#sphx-glr-auto-examples-cluster-plot-agglomerative-dendrogram-py
        """

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

    def inspect_generate_img(self, *, observer_pos, ag: AlgoConfig):
        # REMARK: function is based on modified copy of main plotting function
        data = self.dl.get_data()
        X = generate_input_for_clusteralgo(data)

        # establish DB connection
        # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
        conn = get_db_conn()
        cur = conn.cursor(row_factory=dict_row)

        # Plotting remark: for correct z stacking: plot persistence traces first (would be better to plot *all* persistence traces first, then all current positions)
        fig,hax = self.plot_new()
        # plot persistence (FIXME: no need to loop over all devices currently visible world-wide, just process local ones)
        for q in data:
            curr_devid = q['device']
            timecutoff_epoch = time.time() - ag.device_trace_persistence
            self.plot_device_trace(cur=cur, hax=hax, deviceid=curr_devid, timestamp_min=timecutoff_epoch, kwargs={'color':'b', 'alpha':0.5})
        hax.plot(X[:,1],X[:,0], 'bo', label='rider positions')
        hax.plot(observer_pos[1], observer_pos[0], 'kx', label='center')
        #
        # plot finalization
        # (has to be done for ALL plots before call to 'plot_show_or_save')
        hax.set_xlabel('longitude')
        hax.set_ylabel('latitude')
        # define range (TODO: this is only a very first implementation, it needs to be refined to always show approx +/- 3km of the local "map", independent of latitude)
        drange = 0.03 # for longitude on the equator: approx 3km
        hax.set_xlim(observer_pos[1]-drange,observer_pos[1]+drange)
        hax.set_ylim(observer_pos[0]-drange,observer_pos[0]+drange)
        fig.legend()
        #
        # Store plot
        #
        fn = {} # NOTE: 'fn' is local variable here, not member variable
        my_file_key = 'inspect'
        fn[my_file_key] = self.plot_show_or_save(fig, my_file_key)

        return {'files':fn}

    def geoplot_cluster_analysis(self, *, res:MyResult, plot_config=None):
        pc_name = ''
        pc = None
        if plot_config:
            pc_name = next(iter(plot_config))
            pc = plot_config[pc_name]

        # Note: points that have no neighbor within the distance threshould count as single-element cluster with their own ID
        cluster_labels = res.cluster_labels
        counts_cluster_labels = Counter(cluster_labels)
        counts_cluster_labels = sorted(counts_cluster_labels.items(), key=lambda _: _[1], reverse=True)
        # print(counts_cluster_labels)
        sorted_cluster_ids = [
            # convert np.int64 to int
            int(_[0])
            for _ in counts_cluster_labels
        ]
        # X matrix has to be generated from data that was actually used for the clustering procedure
        # -> then we plot the correct points
        X = generate_input_for_clusteralgo(res.data)

        # prepare plots
        fig,hax = self.plot_new()
        # fig_p,hax_p = self.plot_new({'subplot_kw':{'projection':'polar'}})
        fig_p,hax_p = self.plot_new({'projection':'polar'})
        hax_p.set_rscale('log')

        # For correct z-stacking: plot city limits and all known devices first
        if pc:
            pc['f'](hax)
        if res.ag.exclude_stationary_devices:
            # when the stationary devices are excluded from the data being clustered, be sure to indicate their positions on the map with a different marker style
            data_complete_stationary = list( filter(lambda d: d['flag_in_motion']==0, res.data_complete) )
            Xtmp = generate_input_for_clusteralgo(data_complete_stationary)
            hax.plot(Xtmp[:,1], Xtmp[:,0], '+', color='gray', label='stationary devices')
        if res.ag.exclude_isolated_points:
            # List IDs of single-element clusters
            # (key is cluster ID, value is number of elements)
            single_element_cluster_labels = []
            for cluster_label,cluster_nene in counts_cluster_labels:
                if cluster_nene==1:
                    single_element_cluster_labels.append(int(cluster_label)) # cast to get rid of np.int64
            # Translate collected cluster labels in indices into data matrix
            idx_datapoints_single_element_clusters = []
            for qqq in single_element_cluster_labels:
                idx_datapoints_single_element_clusters.append(
                    [_ for _,x in enumerate(cluster_labels) if x==qqq]
                )
            # FIXME: here we have a nested "list of lists" -> generate single-level list already above?
            from itertools import chain
            idx_datapoints_single_element_clusters = list(chain.from_iterable(idx_datapoints_single_element_clusters))

            Xtmp = generate_input_for_clusteralgo(res.data)
            Xtmp_SEclusters = Xtmp[idx_datapoints_single_element_clusters,:]
            hax.plot(Xtmp_SEclusters[:,1], Xtmp_SEclusters[:,0], 'o', color='gray', markerfacecolor='none', label='single-element "clusters"')

        # Now plot the clusters
        for curr_c in res.cluster_infos:
            # for correct z stacking: plot persistence traces first (would be better to plot *all* persistence traces first, then all current positions)
            curr_color = curr_c.marker_color
            if self.dl.has_data_for_tracepersistence():
                # trace persistence only if data source can provided needed data (currently only for SQL DB)
                self.cluster_plot_persistence(hax=hax, cluster_complete_data=res.data, cluster_labels=cluster_labels, id_cluster=curr_c.cluster_ID, trace_persistence=res.ag.device_trace_persistence, kwargs={'color':curr_color, 'alpha':0.5})
            curr_cluster_center = self.cluster_plot(hax=hax,cluster_data=X,cluster_labels=cluster_labels,id_cluster=curr_c.cluster_ID, indicate_center=True, kwargs={'color':curr_color})
            dist_km_saturated = np.maximum(0.1, np.minimum(curr_c.dist_km, 100)) # elementwise saturation (large values are capped; for small values some radius_minimum is displayed)
            hax_p.plot(np.deg2rad(curr_c.initial_course),dist_km_saturated, 'o',color=curr_color)

        #
        # plot finalization #1
        # (has to be done for ALL plots before call to 'plot_show_or_save')
        hax.plot(res.observer_pos[1], res.observer_pos[0], 'kx', label='your position')
        hax.set_xlabel('longitude')
        hax.set_ylabel('latitude')
        hax.set_title('Result of Clustering Analysis')
        if pc:
            hax.set_xlim(pc['long_range'])
            hax.set_ylim(pc['lat_range'])
        fig.legend()
        #
        # plot finalization #2 (polar plot)
        hax_p.set_title(f'Result of Clustering Analysis (Origin at ({res.observer_pos[0]:.3f},{res.observer_pos[1]:.3f}))')
        hax_p.set_rlim(3e-2, 3e2) # range of radius axis is larger than what is actually used (see elementwise saturation code above): this prevents clipping of the marker on the edges of the coordinate system
        rticks=[0.1, 1, 10, 100]
        hax_p.yaxis.set_major_locator(matplotlib.ticker.FixedLocator(rticks))
        hax_p.set_yticklabels([str(t) for t in rticks])
        hax_p.set_thetagrids([0,90,180,270], ['N (Geographic North)','E','S','W']) # labeling of cardinal directions, labeling N as "Geographic North" to remember user that this is *not* the pointing of the mobile device
        # follow compass conventions
        hax_p.set_theta_zero_location('N')
        hax_p.set_theta_direction(-1)
        #
        # Store plots
        #
        my_file_key = 'clusters'
        if pc:
            my_file_key = 'clusters_'+pc_name
        self.fn[my_file_key] = self.plot_show_or_save(fig, my_file_key)
        if not pc:
            # for polar plot, local plot looks the same (currently only difference for standard plot would be adjustment of coordinate limits and plot of city geographics)
            self.fn[my_file_key+'_polar'] = self.plot_show_or_save(fig_p, my_file_key+'_polar')


    def doit(self, *, res:MyResult):
        # Note: using suitable "shapefiles", you can plot also other maps in the background
        def plot_map_hamburg(hax):
            """
            Helper function to plot geographical information such as city limits
            """
            gdf = gpd.read_file('mapdata/Hamburg_Stadtteilestatistik.shp')
            print(gdf.crs) # info from .prj file

            # Note: could add map using contextily, here we do need Web Mercator (EPSG:3857)
            # list of EPSG codes https://en.wikipedia.org/wiki/EPSG_Geodetic_Parameter_Dataset
            gdf = gdf.to_crs(epsg=4326) # latitude/longitude
            gdf.plot(ax=hax, color='white', edgecolor='grey')

        plot_cfg = {
            # note that the key of the entry becomes part of the filename of any generated image files, use only characters safe in URLs and on all platforms
            'hamburg': {
                'f': plot_map_hamburg, 'lat_range': (53.35, 53.75), 'long_range': (9.7, 10.35)
            }
        }

        # zero out variables we use to collect infos returned to caller at the end of this function
        self.reset_status()

        fig,hax = self.plot_new()
        hax.set_title("Hierarchical Clustering Dendrogram")
        # plot the top three levels of the dendrogram
        self.plot_dendrogram(hax, res.model, truncate_mode="level", p=7, color_threshold=res.ag.cluster_dist_thres)
        hax.set_xlabel("number of points in node (or index of point if no parenthesis)")
        hax.set_ylabel("distance [km]")
        hax.set_ylim(0.1, 3.5*cfg['rho']) # maximum length of great circle is pi*radius
        hax.set_yscale('log')
        self.fn['dendrogram'] = self.plot_show_or_save(fig, 'dendrogram')

        self.geoplot_cluster_analysis(res=res)
        self.geoplot_cluster_analysis(res=res, plot_config=plot_cfg)

        return {'files':self.fn, 'diag_info':self.diag_info, 'clusters':self.cluster_infos}


