#!/usr/bin/env python3

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
from nav import get_nav
from my_util_files import get_list_of_files
from cmaps_util import load_cmap_jsonfile
import psycopg
from psycopg.rows import dict_row
from db_conn import get_db_conn
import datetime
from itertools import cycle


# to have datatype returned by 'AgglomerativeClustering' process for definition of dataclass
import sklearn

@dataclass
class ClusterInfo:
    cluster_ID: int
    latitude: float
    longitude: float
    N: int
    initial_course: float
    dist_km: float
    marker_color: str
    def __str__(self):
        return f"ID={self.cluster_ID}: N={self.N}, center=({self.latitude},{self.longitude}), course={self.course} deg, dist={self.dist}"
    def table_header(self):
        # part of dervied dataclass to ensure that header and string representation of rows have matching layout
        return '<tr><td>(ID)</td><td>N</td><td>center</td><td>course [deg]</td><td>dist [km]</td><td><!-- for inspect link --></td></tr>'
    def as_html(self):
        marker_color_html=matplotlib.colors.to_hex(self.marker_color)
        # replace by jinja template?
        return f"<tr><td style=\"background-color: {marker_color_html}\">{self.cluster_ID}</td><td>{self.N}</td><td>{self.latitude:.2f}, {self.longitude:.2f}</td><td>{self.initial_course:.2f}</td><td>{self.dist_km:.2f}</td><td><a href=\"api/inspect?clat={self.latitude:.6f}&clong={self.longitude:.6f}\" target=\"_blank\">Inspect</a></td></tr>"

@dataclass(frozen=True)
class AlgoConfig:
    exclude_isolated_points: bool    = True
    exclude_stationary_devices: bool = True
    cluster_dist_thres: float        = 2    # km
    device_trace_persistence: float  = 900  # seconds

    def __post_init__(self):
        if self.cluster_dist_thres<=0:
            raise ValueError('value must be positive')


@dataclass(frozen=True)
class MyResult:
        data: list[dict]
        data_complete: list[dict]
        data_timestamp: datetime.datetime
        #
        model: sklearn.cluster._agglomerative.AgglomerativeClustering # result of cluster analysis (needed for dendrogram)
        cluster_labels: list[int]
        cluster_infos: list[ClusterInfo]
        #
        observer_pos: np.array
        #
        ag: AlgoConfig



cfg = {
    'warn_file_age': 120, # seconds
    # 'r_thres': 2, # km, radius used for clustering (note: converted to great-circle angle using radius of Earth)

    ### constants ###
    'rho': 6371, # km, radius of Earth (in spherical approximation)
}

####################
### DATA LOADERS ###
####################
def generate_input_for_clusteralgo(data):
    latitude  = [_['latitude']  for _ in data]
    longitude = [_['longitude'] for _ in data]
    X = np.vstack((np.array(latitude),np.array(longitude)))
    X = np.transpose(X)
    return X


class DataLoader(ABC):
    @abstractmethod
    def get_data(self) -> list[dict]:
        pass

    def has_data_for_tracepersistence(self) -> bool:
        return False

class DataLoaderDB(DataLoader):
    def __init__(self, *, f_factory_DBconn: callable):
        if not callable(f_factory_DBconn):
            raise ValueError('expecting function as argument')
        self.f_factory_DBconn = f_factory_DBconn

    def has_data_for_tracepersistence(self) -> bool:
        return True

    def get_data(self, *, return_all_fields=True) -> list[dict]:
        """
        First implementation to retrieve most recent coordinates seen for every device.
        Uses temporal cut-off. If cut-off time is different from that used by CriticalMaps API server (source of the used data), the data points in the dataset will be different as well -- for instance if a device starts/ceases sending data.
        return_all_fields=False: emulate data structure returned by JSON loading function.
        """
        # print('loading current positions from DB')
        # establish DB connection
        # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
        conn = self.f_factory_DBconn()
        cur = conn.cursor(row_factory=dict_row)

        # A device is considered stationary if it did not report in the previous hour a single position outside of a circle around its last known position
        crit_stationary_radius = 100 # meters
        cur.execute(
            """
            WITH q_ts_mostrecent AS (
                SELECT MAX(timestamp) AS timestamp_mostrecent FROM criticalmaps_data
            ), qq AS (
                SELECT
                    c.deviceid,c.latitude,c.longitude,c.timestamp, ROW_NUMBER() OVER (PARTITION BY c.deviceid ORDER BY c.timestamp DESC) AS rn
                FROM criticalmaps_data AS c, q_ts_mostrecent
                WHERE timestamp>=q_ts_mostrecent.timestamp_mostrecent-150
            )
            SELECT
                deviceid AS device, latitude, longitude, timestamp,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM criticalmaps_data AS c, q_ts_mostrecent
                        WHERE c.deviceid=qq.deviceid
                            -- consider only recent history for checking if there were any movements
                            AND c.timestamp>=q_ts_mostrecent.timestamp_mostrecent-3600
                            -- First spatial filter round: does the cube contain the point (pre-filter that can be indexed)
                            -- TODO: TO BE CHECKED
                            -- AND earth_box(ll_to_earth(qq.latitude,qq.longitude),100) @> ll_to_earth(c.latitude,c.longitude)
                            -- Final spatial filtering round, only has to consider all points in the box
                            AND earth_distance(ll_to_earth(c.latitude,c.longitude),ll_to_earth(qq.latitude,qq.longitude))>=%s
                    )
                    THEN 1 ELSE 0
                END AS flag_in_motion
            FROM qq
            WHERE
                -- be sure that there are not duplicate entries with identical combination of (deviceid;timestamp)
                rn=1;
            """,
            (crit_stationary_radius,)
        )
        res_rows_complete = cur.fetchall()
        if return_all_fields:
            # FIXME: add code to close DB connection
            return res_rows_complete

        # Structure returned from DB has same structure as data loaded from JSON files (containing text obtained from CriticalMaps API interface):
        # A list of dictionaries with the structure: {"device": "...", "latitude": float, "longitude": float, "timestamp": unix_epoch_value}
        # The only difference is that the latitude/longitude values have been scaled to usual (float) values, while the API returns int values (scaled up by a factor of 1E6)
        keys_to_keep = ['device', 'latitude', 'longitude', 'timestamp']
        data = [
            {k: d[k] for k in keys_to_keep}
            for d in res_rows_filt
        ]
        # FIXME: add code to close DB connection
        return data


class DataLoaderTestData(DataLoader):
    def __init__(self):
        pass

    def get_data(self, *, return_all_fields=True) -> list[dict]:
        def make_datapoint(lat,long):
            return {'device':'1234', 'latitude':lat, 'longitude':long, 'timestamp':1}

        print('*** INFO: generating test data set. Still have to implement unique "device IDs" ***')

        # Test data points on the equator (1 deg corresponds to: 2*pi*6371km/360 deg = 111.2 km/deg)
        data = [
            make_datapoint(0,0), make_datapoint(0,0.1), make_datapoint(0,0.3), make_datapoint(0,1), make_datapoint(0,2),
            #
            make_datapoint(0,5),
            make_datapoint(0,5.005), # with rcluster=2km this one will be part of a cluster
            make_datapoint(0,4.98),  # with rcluster=2km this one will not be part of a cluster
        ]

        # Structure returned from DB has same structure as data loaded from JSON files (containing text obtained from CriticalMaps API interface):
        # A list of dictionaries with the structure: {"device": "...", "latitude": float, "longitude": float, "timestamp": unix_epoch_value}
        return data

##############################

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



class MyAnalyzer:
    def __init__(self, dl: DataLoader, *, obj_path=None, fprefix=None):
        """
        dl: Instance of DataLoader-derived class. Contains code for loading the data to be processed. Return 'data' is a list of dicts with the data formatted as in JSON files.
        """

        if not isinstance(dl, DataLoader):
            raise ValueError('expecting DataLoader object')

        # fprefix should be unique to this session
        if fprefix is None:
            fprefix = 'img_123_'

        self.store_plots=False
        if obj_path and isinstance(obj_path,Path):
            self.store_plots=True

        self.dl = dl
        self.fprefix = fprefix
        self.obj_path = obj_path

    def perform_analysis(self, *, observer_pos, ag: AlgoConfig):
        if not isinstance(self.dl, DataLoader):
            raise ValueError('expecting DataLoader object')

        ### HERE WE COLLECT INFOS TO BE RETURNED TO CALLER (= the client via the API server) ###
        diag_info = []
        cluster_infos = []
        fn = {}

        # Note: nomenclature: "complete" means all fields returned from the loader function. If DB is used as data source, additional information may be provided
        data_timestamp_load = datetime.datetime.now()
        data_complete = self.dl.get_data()
        data_complete_moving = list( filter(lambda d: d['flag_in_motion']==1, data_complete) )
        ndev_tot = len(data_complete)
        ndev_moving = len(data_complete_moving)
        diag_info.append(
            f"""
            Breakdown of data:
            Total number of devices: {ndev_tot};
            Number of moving devices: {ndev_moving}
            """
        )

        # Determine what data will be used for cluster analysis
        if ag.exclude_stationary_devices:
            data = data_complete_moving
        else:
            data = data_complete

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
        if len(data)<2:
            raise ValueError(f'Clustering requires at least 2 data points, got {len(data)}') # FIXME: implement better solution that also sends the info what happened to the Web/API User
        X = generate_input_for_clusteralgo(data)
        # for the clustering algorithm, we need long/lat in radians
        Xrad = np.radians(X)

        Xmetric = haversine_distances(Xrad)
        Xmetric = cfg['rho']*Xmetric
        # print(Xmetric)
        # print(X)

        ### TODO: understand what the default linkage 'ward' does

        # setting distance_threshold=0 ensures we compute the full tree.
        mu_thres = ag.cluster_dist_thres/cfg['rho']
        model = AgglomerativeClustering(metric='haversine', linkage='single', distance_threshold=mu_thres, n_clusters=None)
        cluster_labels = model.fit_predict(Xrad)
        # print(cluster_labels)


        """
        Now the dataset is divided into clusters -> analyze them.
        """
        # Note: points that have no neighbor within the distance threshould count as single-element cluster with their own ID
        counts_cluster_labels = Counter(cluster_labels)
        counts_cluster_labels = sorted(counts_cluster_labels.items(), key=lambda _: _[1], reverse=True)
        # print(counts_cluster_labels)
        sorted_cluster_ids = [
            # convert np.int64 to int
            int(_[0])
            for _ in counts_cluster_labels
        ]


        # Colors we use to indicate cluster points.
        # These are the matplotlib default colors except gray, https://matplotlib.org/stable/gallery/color/color_cycle_default.html
        # Gray is used to indicate city limits, devices that are not considered for cluster analysis because they are stationary, etc.
        iter_colors = cycle(['blue','orange','green','red','purple','brown','pink','olive','cyan'])
        for id_cluster in sorted_cluster_ids:
            # if requested by user, ignore single-element 'clusters'
            curr_cluster_nele = dict(counts_cluster_labels)[id_cluster]
            if ag.exclude_isolated_points and curr_cluster_nele<=1:
                continue

            # assign colors already here
            curr_color=next(iter_colors)

            curr_cluster_center = cluster_compute_center(cluster_data=X, cluster_labels=cluster_labels, id_cluster=id_cluster)
            initial_course,dist_rad = get_nav(observer_pos, curr_cluster_center)
            dist_km = cfg['rho']*dist_rad
            curr_ci = ClusterInfo(cluster_ID=id_cluster, N=curr_cluster_nele, latitude=curr_cluster_center[0], longitude=curr_cluster_center[1], initial_course=initial_course, dist_km=dist_km, marker_color=curr_color)
            cluster_infos.append(curr_ci)


        print('TODO: record diag_info somewhere')
        return MyResult(
            data_timestamp=data_timestamp_load,
            # complete data set
            data_complete=data_complete,
            # data actually used for analysis (depending on configuration settings, this can be a subset of all data points)
            data=data,
            #
            model = model, # retain the result of the analysis for dendrogram generation
            cluster_labels=cluster_labels,
            cluster_infos=cluster_infos,
            #
            observer_pos=observer_pos,
            #
            ag=ag
        )
        # return {'files':fn, 'diag_info':diag_info, 'clusters':cluster_infos}


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


if __name__=='__main__':
    # fixed dummy position in Hamburg for dev purposes
    my_pos = np.array([53.55, 10.0])

    def cb_age(age):
        if age>cfg['warn_file_age']:
            # diag_info.append(f'WARNING: file is {age} seconds old') # FIXME
            print(f'WARNING: file is {age} seconds old')

    def dataloader_file(datafile, spatial_filter=None):
        """
        datafile: name of file to be loaded (NOTE: functools.partial can be used to obtain a function with frozen argument values to be passed to the data processing function)
        spatial_filter: function used for spatial filtering. Takes single argument (JSON data point) and returns True if point is to be retained
        """
        print(f'loading data from file {datafile}')
        data,X = load_cmap_jsonfile(datafile, spatial_filter=spatial_filter, cb_diag_file_age=cb_age)
        return data

    # hard-coded test data for clustering algorithm
    # r = main(f_dataloader=load_clustertestdata, observer_pos=my_pos, exclude_isolated_points=False)

    # load data from JSON file
    # r = main(f_dataloader=partial(dataloader_file, datafile='cmdata/data_20260528T100900_002729.json'), observer_pos=my_pos, exclude_isolated_points=False)

    # default loader is DB loader
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn)
    my_a = MyAnalyzer(dl=my_dl)
    res = my_a.perform_analysis(observer_pos=my_pos, ag = AlgoConfig(exclude_isolated_points = False))
    print(res)
    my_p = MyPlotter(dl=my_dl)
    my_p.doit(res=res)
