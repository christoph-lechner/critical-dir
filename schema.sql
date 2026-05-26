CREATE TABLE criticalmaps_data(
    _h TEXT,
    deviceid TEXT,
    longitude FLOAT,
    latitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);
