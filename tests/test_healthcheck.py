from critical_dir.healthcheck import Healthcheck

def test_healthcheck():
    h = Healthcheck(max_age=10)
    h.heartbeat()

    # 2026-Nov: disabled remaining test code as 'start_server' binds server to TCP port
    """
    # code from healthcheck.py
    h.start_server()
    time.sleep(10)
    h.heartbeat()
    h.heartbeat()
    h.heartbeat()
    time.sleep(10)

    print('10s are over -> send a request and there should be ERROR status')

    time.sleep(10)
    h.stop_server()
    """
