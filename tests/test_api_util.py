from critical_dir.api_util import generate_cache_key
from critical_dir.criticaldir_core import AlgoConfig


def test_gen_cache_key():
    # simple test verifying that class that is used as part of redis cache key can be hashed without crashing

    ag = AlgoConfig()
    generate_cache_key(ag)

    ag = AlgoConfig(
        exclude_isolated_points=True,
        exclude_stationary_devices=True, 
        cluster_dist_thres=0.5,
        device_trace_persistence=900
    )
    generate_cache_key(ag)
