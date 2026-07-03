

-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats(
	id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,

	ts TIMESTAMP WITH TIME ZONE,
	total_time FLOAT,
	total_status BOOLEAN,

	-- these are NULL in case of no exception
	exc_inphase TEXT,
	exc_name TEXT, 
	exc_info TEXT,

	api_http_response_code INT,

	fileok BOOLEAN,
	filename TEXT,
	nrows_loaded INT,
	nrows_inserts INT,
	nrows_updates INT,
	nrows_quarantine INT
);





-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
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

