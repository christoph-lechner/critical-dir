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
