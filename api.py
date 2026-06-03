#!/usr/bin/env python3

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,Response
from fastapi import Request
from pydantic import BaseModel

import numpy as np
from pathlib import Path
import datetime

from criticaldir_core import MyAnalyzer,MyPlotter,DataLoaderDB,AlgoConfig
from db_conn import get_db_conn

class ClustersResponseItem(BaseModel):
    cluster_ID: int
    center_latitude: float
    center_longitude: float
    N: int
class ClustersResponse(BaseModel):
    info: str
    clusters: list[ClustersResponseItem]

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: float
    timestamp: int
    cfg_flag_iso: bool
    cfg_flag_exclude_stationary: bool
    cfg_cluster_dist: float = 2   # km
    cfg_tpersistence: float = 900 # seconds

class LocationResponse(BaseModel):
    html: str
    diag: str



app = FastAPI(
    docs_url=None,          # disables /docs
    redoc_url=None,         # disables /redoc
    openapi_url=None,       # disables /openapi.json
)

app.mount('/objs', StaticFiles(directory='objs'), name='objs')

@app.get('/', response_class=HTMLResponse)
async def req_catch_all(request: Request):
    html = "<html><body><h1>Home Page</h1><hr>This demonstrates that the server can be reached.</body></html>"
    return HTMLResponse(content=html)


###############################################################################################
### /location is the main workhorse, requests from WebApp for data on overview page go here ###
###############################################################################################

def clusters_worker(*, ag):
    # use DB for current positions
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn)
    my_a = MyAnalyzer(dl=my_dl)
    user_pos = np.array([53.55, 10.0]) # dummy position, we only return clusters without direction information
    res = my_a.perform_analysis(observer_pos=user_pos, ag=ag)
    # print(res.cluster_infos)

    # To be JSON serializable, the returned object has to be an instance of the defined pydantic class.
    # Some of the fields that come from the analysis process should be shadowed from the client, such as course/distance because at dummy user_position had to be provided
    r = []
    for ci in res.cluster_infos:
        r.append({'cluster_ID':ci.cluster_ID, 'center_latitude':ci.latitude, 'center_longitude':ci.longitude, 'N':ci.N})
    return r

def location_worker(user_pos, *, ag):
    # store timestamp
    tic = datetime.datetime.now()

    # generate "unique" prefix for image files
    tstr = tic.strftime('%Y%m%dT%H%M%S.%f')
    fprefix = f'img_{tstr}_'

    # use DB for current positions
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn)
    my_a = MyAnalyzer(dl=my_dl, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix=fprefix)
    res = my_a.perform_analysis(observer_pos=user_pos, ag=ag)
    my_p = MyPlotter(
        dl=my_dl,
        obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix=fprefix
    )
    r = my_p.doit(res=res)


    diag_info = '<h3>Diag Infos</h3>'
    diag_info += f'Server time: {tstr}<br>'
    diag_info += '<ul>'
    for di in r['diag_info']:
        diag_info += '<li>'+di
    diag_info += '</ul>'


    def ci_as_table(lci):
        """
        Converts list of ClusterInfo instances to HTML table
        """
        r = "<table>\n"
        if len(lci)>0:
            r += lci[0].table_header()
            for x in lci:
                r += x.as_html() + '\n'
        else:
            r += '<tr><td><font color=red>(no clusters match current criteria)</font></td></tr>'
        r += "</table>\n"
        return r

    # ci = r['clusters']
    ci = res.cluster_infos
    ci = sorted(ci, key=lambda _: (_.N,(-1)*_.dist_km), reverse=True) # Note: tuple as sort key -> force sort order for clusters with identical N, list closer clusters first (if first element is identical, second element determines sort order)
    ci_dist = sorted(ci, key=lambda _: _.dist_km, reverse=False)
    html_info  = ''
    html_info += '<h3>Clusters (lowest distance first)</h3>'
    html_info += ci_as_table(ci_dist)
    html_info += '<h3>Clusters (largest cluster first)</h3>'
    html_info += ci_as_table(ci)

    # Keys of images to present FIRST (in this order)
    top_files = ['clusters_polar','clusters_hamburg','clusters']

    html_imgs = ""
    print(r['files'])
    def html4img(k):
        def get_img_loc(k):
            return 'api/objs/' + r['files'][k]
        return f'<img src="{ get_img_loc(k) }"><br>'
    ### top imgs
    for k in top_files:
        if not k in r['files']:
            print(f'WARNING: key {k} not found in list of files')
            continue
        html_imgs += html4img(k)
    ### all other images
    for k in r['files'].keys():
        if k in top_files:
            continue
        html_imgs += html4img(k)

    # store timestamp
    toc = datetime.datetime.now()
    deltat = toc-tic
    deltat = deltat.total_seconds()
    diag_info += f'<p>total processing time: {deltat:.2f} seconds'

    return {
        'html': html_info+'<h3>Plots generated by server</h3>'+html_imgs,
        'diag': diag_info
    }

@app.get('/clusters', response_model=ClustersResponse)
def get_clusters():
    # for the demo, some hard-coded defaults
    ag = AlgoConfig(
        exclude_isolated_points=False,    #True,
        exclude_stationary_devices=False, #True, 
        cluster_dist_thres=1.0,
        device_trace_persistence=900
    )
    clusters=clusters_worker(ag=ag)
    r = {
        'info': 'parameters_for_the_cluster_analysis_go_here',
        'clusters': clusters
    }
    # TODO: Ideas what should also be part of the response:
    # lat/long of all cluster members (maybe also their device IDs?)
    return r


@app.post('/location_demo', response_model=LocationResponse)
@app.get('/location_demo', response_model=LocationResponse)
def update_location_demo():
    """
    Implements location API endpoint for DEMO
    (input: does not require coordinates, uses hard-coded user-coordinates)
    """
    # fixed dummy position in Hamburg for dev/demo
    user_pos = np.array([53.55, 10.0])
    ag = AlgoConfig(
        exclude_isolated_points=payload.cfg_flag_iso,
        exclude_stationary_devices=payload.cfg_flag_exclude_stationary, 
        cluster_dist_thres=payload.cfg_cluster_dist,
        device_trace_persistence=payload.cfg_tpersistence
    )
    return location_worker(user_pos, ag=ag)

@app.post('/location', response_model=LocationResponse)
def update_location(payload: LocationRequest):
    """
    Implements location API endpoint
    """
    user_pos = np.array([payload.latitude, payload.longitude])
    ag = AlgoConfig(
        exclude_isolated_points=payload.cfg_flag_iso,
        exclude_stationary_devices=payload.cfg_flag_exclude_stationary, 
        cluster_dist_thres=payload.cfg_cluster_dist,
        device_trace_persistence=payload.cfg_tpersistence
    )
    return location_worker(user_pos, ag=ag)


def inspect_worker(lat: float, long: float) -> str:
    return 'hallo'

@app.get('/inspect', response_class=HTMLResponse)
async def inspect(clat: float, clong: float):
    # generate "unique" prefix for image files
    tnow = datetime.datetime.now()
    tstr = tnow.strftime('%Y%m%dT%H%M%S.%f')
    fprefix = f'img_{tstr}_'

    fn_img = inspect_worker(lat=clat, long=clong)
    my_dl = DataLoaderDB(f_factory_DBconn=get_db_conn)
    my_a = MyAnalyzer(dl=my_dl, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix=fprefix)
    my_p = MyPlotter(
        dl=my_dl,
        obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix=fprefix
    )
    r = my_p.inspect_generate_img(observer_pos=[clat,clong], ag=AlgoConfig())

    fn_img = r['files']['inspect']
    html = f"<html><body><a href=/myapp/>For iPhone PWA: Back</a><p>Inspecting local distribution of riders around {clat:.4f},{clong:.4f}. Note that this plot does not indicate cluster infos, so all positions are indicated with same marker color.<img src=\"objs/{fn_img}\"></body></html>"
    return HTMLResponse(content=html)



if __name__=="__main__":
    uvicorn.run(
        app,
        host='0.0.0.0', port=8777,
        server_header=False, # <- don't send "server: uvicorn" in response
    )
