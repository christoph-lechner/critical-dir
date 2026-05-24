#!/usr/bin/env python3

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,Response
from fastapi import Request
from pydantic import BaseModel

from w import main
import numpy as np
from pathlib import Path
import datetime

class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    accuracy: float
    timestamp: int

class LocationResponse(BaseModel):
    html: str
    diag: str

app = FastAPI(
    docs_url=None,          # disables /docs
    redoc_url=None,         # disables /redoc
    openapi_url=None,       # disables /openapi.json
)

app.mount('/objs', StaticFiles(directory='objs'), name='objs')

@app.post('/location', response_model=LocationResponse)
def update_location(payload: LocationRequest):
    # business logic
    print(payload)

    # fixed dummy position in Hamburg for dev purposes
    my_pos = np.array([10, 53.5])

    tnow = datetime.datetime.now()
    fprefix = tnow.strftime('img_%Y%m%dT%H%M%S.%f_')
    my_pos = np.array([payload.longitude, payload.latitude])
    r = main(datafile='data.json', observer_pos=my_pos, obj_path=Path('/home/cl/work/criticalmaps--richtungspfeil/objs/'), fprefix=fprefix)

    html_imgs = ""
    for f in r['files']:
        def get_img_loc(f):
            return f'api/objs/{fprefix}{f}.png'
        html_imgs += f'<img src="{ get_img_loc(f) }"><br>'


    diag_info = '<h3>Diag Infos</h3>'
    diag_info += '<ul>'
    for di in r['diag_info']:
        diag_info += '<li>'+di
    diag_info += '</ul>'


    def ci_as_table(ci):
        r = "<table>"
        r += ci[0].table_header()
        for x in ci:
            r += x.as_html()
        r += "</table>"
        return r

    ci = r['clusters']
    ci = sorted(ci, key=lambda _: _.N, reverse=True)
    ci_dist = sorted(ci, key=lambda _: _.dist, reverse=False)
    diag_info += '<h3>Clusters (lowest distance first)</h3>'
    diag_info += ci_as_table(ci_dist)
    diag_info += '<h3>Clusters (largest cluster first)</h3>'
    diag_info += ci_as_table(ci)


    return {
        'html': '<h2>Hello from FastAPI</h2>'+html_imgs,
        'diag': diag_info
    }

@app.get('/', response_class=HTMLResponse)
async def req_catch_all(request: Request):
    html = "<html><body><h1>Home Page</h1><hr>This demonstrates that the server can be reached.</body></html>"
    return HTMLResponse(content=html)

if __name__=="__main__":
    uvicorn.run(
        app,
        host='0.0.0.0', port=8777,
        server_header=False, # <- don't send "server: uvicorn" in response
    )
