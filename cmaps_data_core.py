import requests

def get_cmaps_data():
    # API URL and Headers from network traffic of CriticalMaps Web Map
    api_url = 'https://api-cdn.criticalmaps.net/locations'
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Referer': 'https://www.criticalmaps.net/',
        'Origin': 'https://www.criticalmaps.net',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'Priority': 'u=4',
        'TE': 'trailers'
    }
    """
    # But it turns out the headers are not needed.
    headers = {}

    r = requests.get(api_url, headers=headers)
    r.raise_for_status()
    return r.text
