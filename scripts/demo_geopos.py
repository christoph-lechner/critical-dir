#!/usr/bin/env python3

"""
Demo script using directory access to database.

Download all geopositions from the database and indicate them on a map.

Uses coastline data from https://www.naturalearthdata.com/downloads/110m-physical-vectors/110m-coastline/
"""

import psycopg
from psycopg.rows import dict_row
from critical_dir.db_conn import get_db_conn
import matplotlib.pyplot as plt
import geopandas as gpd

def main():
    # establish DB connection
    # (https://www.psycopg.org/psycopg3/docs/advanced/rows.html#row-factories)
    conn = get_db_conn()
    cur = conn.cursor(row_factory=dict_row)

    cur.execute(
        """
        SELECT latitude,longitude FROM criticalmaps_data ORDER BY 1 ASC, 2 ASC;
        """
    )
    res = cur.fetchall()
    data_lat  = [_['latitude'] for _ in res]
    data_long = [_['longitude'] for _ in res]

    coastlines = gpd.read_file('ne_110m_coastline.zip')

    fig,hax = plt.subplots(1)
    coastlines.plot(ax=hax, color='gray', linewidth=0.5)
    hax.plot(data_long, data_lat, '.')
    hax.set_xlabel('longitude')
    hax.set_ylabel('latitude')
    hax.set_xlim(-180,180)
    hax.set_ylim(-90,90)
    plt.show()

    conn.close()

if __name__=='__main__':
    main()
