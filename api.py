#!/usr/bin/env python3

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse,Response
from fastapi import Request
from pydantic import BaseModel

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

    return {
        'html': '<p>Hello from FastAPI <img src="api/objs/plot1.png">',
        'diag': 'diag_info'
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
