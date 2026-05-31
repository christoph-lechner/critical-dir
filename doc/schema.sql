-- NOTE: if you change the definition of this table, be sure to update the data ingestion script
CREATE TABLE criticalmaps_data(
    _h TEXT,
    deviceid TEXT,
    longitude FLOAT,
    latitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);

-- index supporting for instance searches for a specific device ID (and additional temporal filtering)
CREATE INDEX ON criticalmaps_data(deviceid,timestamp);
-- index supporting geographical queries such as "WHERE latitude BETWEEN 53.35 AND 53.75 AND longitude BETWEEN 9.7 AND 10.35" (bounding box of city of Hamburg)
CREATE INDEX ON criticalmaps_data(latitude,longitude);
-- index for queries such as "SELECT MAX(timestamp) AS timestamp_mostrecent FROM criticalmaps_data"
CREATE INDEX ON criticalmaps_data(timestamp);
