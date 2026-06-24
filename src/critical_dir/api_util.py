import json
import hashlib
from dataclasses import asdict

def generate_cache_key(params, *, prefix='my_computation', verbose=False):
    payload = json.dumps(
        asdict(params),
        sort_keys=True,
        separators=(", ", ":"),
    )
    if verbose:
        print(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f'{prefix}:{digest}'

def determine_cache_ttl(data_age):
    """
    Function to determine time-to-live (TTL) for object storage in redis cache.

    'data_age': how far back in time is the "time of interest"?
    """
    if data_age<120:
        # most recent data is cached with a short time-to-live (client refresh period is 30 seconds, using
        # a little-bit-longer value so that the actual computation is not always triggered by the same client)
        return 35

    # using longer cache time-to-live here (not expecting updates of underlying data here)
    return 900
