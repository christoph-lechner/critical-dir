import numpy as np
# from scipy.cluster.hierarchy import dendrogram
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import haversine_distances
from collections import Counter
from pathlib import Path
from dataclasses import dataclass
from abc import ABC, abstractmethod
from .nav import get_nav
from .exceptions import EInsufficientData, ENoData
from psycopg.rows import dict_row
import datetime
from itertools import cycle

# colors used in code for HTML format
import matplotlib

# to have datatype returned by 'AgglomerativeClustering' process for definition of dataclass
import sklearn

@dataclass(frozen=True)
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
    def make_openstreetmap_url(self):
        return f'https://www.openstreetmap.org/#map=14/{self.latitude:.2f}/{self.longitude:.2f}'
    def as_html(self, *, with_inspect_link=True):
        marker_color_html=matplotlib.colors.to_hex(self.marker_color)

        # replace by jinja template?
        inspect_link = '' # default: do not emit "inspect" link
        if with_inspect_link:
            inspect_link = f'<a href="api/inspect?clat={self.latitude:.6f}&clong={self.longitude:.6f}" target="_blank">Inspect</a>'
        return f"<tr><td style=\"background-color: {marker_color_html}\">{self.cluster_ID}</td><td>{self.N}</td><td><a href=\"{self.make_openstreetmap_url()}\" target=\"_blank\">{self.latitude:.2f}, {self.longitude:.2f}</a></td><td>{self.initial_course:.2f}</td><td>{self.dist_km:.2f}</td><td>{inspect_link}</td></tr>"

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
    def __init__(self, *, f_factory_DBconn: callable, t0: int=None):
        if not callable(f_factory_DBconn):
            raise ValueError('expecting function as argument')
        self.f_factory_DBconn = f_factory_DBconn

        self.supports_tracepersistence = True
        self.t0 = None
        if t0:
            self.supports_tracepersistence = False
            self.t0 = t0

    def has_data_for_tracepersistence(self) -> bool:
        return (self.supports_tracepersistence) # no trace persistence for "wayback machine mode"

    def get_data_newest_timestamp(self) -> float:
        """
        Function obtains most recent timestamp from database.
        Possible application: check freshness of data.
        """
        # establish DB connection
        # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
        conn = self.f_factory_DBconn()
        cur = conn.cursor(row_factory=dict_row)

        # Timestamps are stored as UNIX epoch, get most recent timestamp value from DB
        cur.execute("SELECT MAX(timestamp) AS m FROM criticalmaps_data;")
        res = cur.fetchall()
        if len(res)==0:
            raise ValueError('no data from DB while checking age of data')
        max_timestamp = res[0]['m']

        # FIXME: add code to close DB connection
        return max_timestamp

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

        # Dynamic generation of subquery, depending on operation mode (current or historic data)
        # (1) standard operation, temporal cutoff defined by most recent timestamp in database
        subquery_cutoff = 'SELECT MAX(timestamp) AS timestamp_mostrecent FROM criticalmaps_data'
        if self.t0:
            # (2) special operation mode to look back at historic data
            subquery_cutoff = f'SELECT {self.t0} AS timestamp_mostrecent'

        query_params = {
            'rho_min': crit_stationary_radius,
        }
        cur.execute(
            f"""
            WITH q_ts_cutoff AS (
                -- SELECT MAX(timestamp) AS timestamp_mostrecent FROM criticalmaps_data
                { subquery_cutoff }
            ), qq AS (
                SELECT
                    c.deviceid,c.latitude,c.longitude,c.timestamp, ROW_NUMBER() OVER (PARTITION BY c.deviceid ORDER BY c.timestamp DESC) AS rn
                FROM criticalmaps_data AS c, q_ts_cutoff
                WHERE
                    c.timestamp>=q_ts_cutoff.timestamp_mostrecent-150
                    -- this condition only has an effect if we obtain data from the past
                    AND q_ts_cutoff.timestamp_mostrecent>=c.timestamp
            )
            SELECT
                deviceid AS device, latitude, longitude, timestamp,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM criticalmaps_data AS c, q_ts_cutoff
                        WHERE
                            c.deviceid=qq.deviceid
                            --
                            -- consider only recent history for checking if there were any movements
                            AND c.timestamp>=q_ts_cutoff.timestamp_mostrecent-3600
                            -- this condition only has an effect if we obtain data from the past
                            AND q_ts_cutoff.timestamp_mostrecent>=c.timestamp
                            --
                            -- First spatial filter round: does the cube contain the point (pre-filter that can be indexed)
                            -- TODO: TO BE CHECKED
                            -- AND earth_box(ll_to_earth(qq.latitude,qq.longitude),100) @> ll_to_earth(c.latitude,c.longitude)
                            -- Final spatial filtering round, only has to consider all points in the box
                            AND earth_distance(ll_to_earth(c.latitude,c.longitude),ll_to_earth(qq.latitude,qq.longitude))>=%(rho_min)s
                    )
                    THEN 1 ELSE 0
                END AS flag_in_motion
            FROM qq
            WHERE
                -- be sure that there are not duplicate entries with identical combination of (deviceid;timestamp)
                rn=1;
            """,
            query_params
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
    """
    Note: test data is used for automatic testing of clustering algorithm,
    do not modify this class without considering impact on automatic tests.
    As of June-2026, there are two types of tests depending on this data:
    - tests with pytest
    - tests of the API server / Docker image
    """
    def __init__(self):
        self.id_datapoint = 0

    def get_datapoint_id(self):
        self.id_datapoint += 1
        return self.id_datapoint

    def get_data(self, *, return_all_fields=True) -> list[dict]:
        def make_datapoint(lat,long):
            return {
                'device':str(self.get_datapoint_id()),
                'latitude':lat,
                'longitude':long,
                'timestamp':1,
                # 2026-06-03: add the in-motion flag to the test dataset as analysis algorithm breaks otherwise. This should be improved in the future because this flag is not in the original JSON format (FIXME?)
                'flag_in_motion':1
            }

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
    is_in_bbox = (9.7<=longitude) and (longitude<=10.35) and (53.35<=latitude) and (latitude<=53.75) # noqa: PLR1716
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
        # fn = {}

        # Note: nomenclature: "complete" means all fields returned from the loader function. If DB is used as data source, additional information may be provided
        data_timestamp_load = datetime.datetime.now(tz=datetime.timezone.utc)
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
        if len(data)==0:
            raise ENoData('')
        elif len(data)<2:
            raise EInsufficientData(f'Clustering requires at least 2 data points, got {len(data)}')
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
        # Note: points that have no neighbor within the distance threshold count as single-element cluster with their own ID
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

