import json
import numpy as np
import os
import time

class BadJSONDataFile(Exception):
    """ Raised when JSON file has unexpected structure """
    def __init__(self, str_info: str):
        super().__init__(f'Unexpected format of JSON file: {str_info}')
        self.str_info = str_info

def normalize_coords(d):
    """
    The JSON contains the geolocation data as Int, scaled by 1E6.
    Does not modify or remove any other fields.
    """
    def my_helper(d,key):
        if key in d:
            d[key] = d[key]/1.0e6
    my_helper(d,'longitude')
    my_helper(d,'latitude')
    return d

def load_cmap_jsonfile(datafile, *, spatial_filter=None, cb_diag_file_age=None):
    # Check age of data file (note: using functions returning ints to avoid loss of precision caused by floats)
    statinfo = os.stat(datafile)
    # print(statinfo.st_mtime)
    age_datafile = time.time_ns()/1000000000 - statinfo.st_mtime
    if cb_diag_file_age and callable(cb_diag_file_age):
        cb_diag_file_age(age_datafile)

    with open(datafile,'r') as fin:
        data_all = json.load(fin)

    # expecting JSON file to contain a list
    if not isinstance(data_all, list):
        raise BadJSONDataFile('expecting JSON file to contain a list')

    def check_fields(d, keys):
        """
        'd': dict to check
        'keys': list of keys to look for
        """
        for k in keys:
            if not k in d:
                raise BadJSONDataFile(f'missing field "{k}"')

    data = []
    for d in data_all:
        # before doing any work, check if the needed fields are present
        check_fields(d, ['longitude','latitude','device','timestamp'])

        d = normalize_coords(d)
        if spatial_filter and callable(spatial_filter) and spatial_filter(d)==False:
            continue
        data.append(d)

    longitude = [_['longitude'] for _ in data]
    latitude  = [_['latitude']  for _ in data]

    #fig,hax = plot_new()
    #hax.plot(longitude, latitude, 'o')
    #hax.set_title('Points as loaded from JSON Data')
    #fn['scatter'] = plot_show_or_save(fig,'scatter')

    X = np.vstack((np.array(longitude),np.array(latitude)))
    X = np.transpose(X)
    # print(X)

    return data,X

