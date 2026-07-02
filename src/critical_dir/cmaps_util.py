import json
import os
import time
from pydantic import BaseModel, PositiveInt, TypeAdapter

# "raw" data type (as delivered by server API)
class DeviceUpdateRaw(BaseModel):
    device: str
    latitude: int
    longitude: int
    timestamp: PositiveInt

# data type with normalized latitude/longitude
class DeviceUpdate(BaseModel):
    device: str
    latitude: float
    longitude: float
    timestamp: PositiveInt

class BadJSONDataFile(Exception):
    """ Raised when JSON file has unexpected structure """
    def __init__(self, str_info: str):
        super().__init__(f'Unexpected format of JSON file: {str_info}')
        self.str_info = str_info

def load_cmap_jsonfile(datafile, *, spatial_filter=None, cb_diag_file_age=None):
    # Check age of data file (note: using functions returning ints to avoid loss of precision caused by floats)
    statinfo = os.stat(datafile)
    # print(statinfo.st_mtime)
    age_datafile = time.time_ns()/1000000000 - statinfo.st_mtime
    if cb_diag_file_age and callable(cb_diag_file_age):
        cb_diag_file_age(age_datafile)

    with open(datafile,'r') as fin:
        json_string = fin.read()

    deviceupdate_list_adapter = TypeAdapter(list[DeviceUpdateRaw])
    data_raw = deviceupdate_list_adapter.validate_json(json_string)

    # expecting JSON file to contain a list
    if not isinstance(data_raw, list):
        raise BadJSONDataFile('expecting JSON file to contain a list')

    data = []
    for draw in data_raw:
        """
        The JSON contains the geolocation data as Int, scaled by 1E6.
        Does not modify or remove any other fields.
        """
        d = DeviceUpdate(
                device    = draw.device,
                latitude  = draw.latitude/1.0e6,
                longitude = draw.longitude/1.0e6,
                timestamp = draw.timestamp
            )
        if spatial_filter and callable(spatial_filter) and spatial_filter(d)==False:
            continue
        data.append(d)

    return data
