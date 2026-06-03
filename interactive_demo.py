#!/usr/bin/env python3

import datetime
from zoneinfo import ZoneInfo
from criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderDB,AlgoConfig
from db_conn import get_db_conn

def main():
    # fixed dummy position in Hamburg for dev purposes
    my_pos = [53.55, 10.0]

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


    # We use the "DB loader"
    # Other interesting timestamps are
    # - UNIX epoch=1780239180, Sun., 31.05.2026, 16:53
    # - UNIX epoch=1780080600, Fri., 29.05.2026, 20:50
    dt = datetime.datetime(2026,5,29, 19,45, tzinfo=ZoneInfo('Europe/Berlin'))
    epoch = int(dt.timestamp())
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn, t0=epoch)
    my_a = MyAnalyzer(dl=my_dl)
    res = my_a.perform_analysis(
        observer_pos=my_pos,
        ag = AlgoConfig(exclude_isolated_points = True, cluster_dist_thres=0.3)
    )
    print(res)
    my_p = MyPlotter(dl=my_dl)
    my_p.doit(res=res)

if __name__=='__main__':
    main()
