#!/usr/bin/env python3

# Christoph Lechner, 2025-Nov-27
#
# Simple health monitoring via HTTP

# FIXME: if instance of Healthcheck is destroyed, we cannot ask for the
# server to stop. Then the port may still be occupied until Python exits.

import threading
from queue import Queue
import threading
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse,Response
from dataclasses import dataclass
import datetime
import time

@dataclass
class Healthcheck_Msg:
    ts_send: datetime.datetime
    is_heartbeat: bool = True

class Healthcheck:
    # class variable is shared by all instances
    q = Queue()
    # class variable to be able to stop server
    server = None

    def __init__(self, *, http_port=8080, max_age=-1):
        self.http_port = http_port
        self.max_age=max_age

    def run_server(self,server):
        server.run()

    ##################################
    ### Interface for main program ###
    ##################################

    def start_server(self):
        #if self.tsrv:
        #    raise ValueError('Server thread already running')

        app = FastAPI(
            docs_url=None,          # disables /docs
            redoc_url=None,         # disables /redoc
            openapi_url=None,       # disables /openapi.json
        )
        # shared status structure
        app.state.s = {
            'ts_last_heartbeat': None
        }

        ### implements the watchdog logic ###
        def check_worker():
            # process any heartbeat messages
            while not self.q.empty():
                msg = self.q.get()
                if (not app.state.s['ts_last_heartbeat']) or (msg.ts_send>app.state.s['ts_last_heartbeat']):
                    app.state.s['ts_last_heartbeat']=msg.ts_send
            # print(app.state.s)
            
            # If no heartbeat was received so far: bad state
            #    (we don't know the reason why no heartbeat was received)
            if not app.state.s['ts_last_heartbeat']:
                return False

            tnow = datetime.datetime.now()
            deltat = tnow - app.state.s['ts_last_heartbeat']
            if deltat.total_seconds()>self.max_age:
                return False
            return True # time criterion is met

        @app.get('/check', response_class=HTMLResponse)
        def check():
            status_ok = check_worker()
            if status_ok:
                return HTMLResponse(content='OK')
            return HTMLResponse(content='ERROR', status_code=500)

        @app.head('/check')
        def check_head():
            status_ok = check_worker()
            if status_ok:
                return Response(status_code=200)
            return Response(status_code=500)

        # 404 catch-all response for any unexpected URLs
        @app.get('/{full_path:path}', response_class=HTMLResponse)
        async def catch_all(full_path: str):
            html = f'<html><body><h1>404 - page not found</h1><p>Requested resource /{full_path} not found</body></html>'
            return HTMLResponse(content=html, status_code=404)

        config = uvicorn.Config(
            app,
            host='0.0.0.0', port=self.http_port,
            server_header=False, # <- don't send "server: uvicorn" in response
        )
        self.server = uvicorn.Server(config)
        # launch thread
        self.tsrv = threading.Thread(target=self.run_server, args=(self.server,), daemon=True)
        self.tsrv.start()

    def stop_server(self):
        # if server was launched: trigger graceful shutdown of server
        if self.server:
            self.server.should_exit=True
            self.server=None

        # wait for thread to exit: this ensures that the TCP port can be used again
        self.tsrv.join()

    def heartbeat(self):
        msg = Healthcheck_Msg(ts_send=datetime.datetime.now())
        self.q.put(msg)

# Simple demo
# -> consider running 'pytest' to use the tests that come with this class
if __name__=='__main__':
    h = Healthcheck(max_age=10)
    h.heartbeat()
    h.start_server()
    time.sleep(10)
    h.heartbeat()
    h.heartbeat()
    h.heartbeat()
    time.sleep(10)

    print('10s are over -> send a request and there should be ERROR status')

    time.sleep(10)
    h.stop_server()
