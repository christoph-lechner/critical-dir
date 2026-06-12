#!/usr/bin/env python3

"""
Helper script for testing of Docker image using a postgreSQL DB
populated with test data. To be consistent, the test data generator
also used when verifying the clustering algorithms is used.
"""

from critical_dir.criticaldir_core import DataLoaderTestData

def main():
    dl = DataLoaderTestData()
    data = dl.get_data()

    for d in data:
        # this is test data: to meet the UNIQUE constraint on '_h', we use the device id also to populate _h.
        fake_hash = d['device']
        print(f"INSERT INTO criticalmaps_data (_h,deviceid,latitude,longitude,timestamp) VALUES ('{fake_hash}','{d['device']}',{d['latitude']},{d['longitude']},{d['timestamp']});")

if __name__=='__main__':
    main()
