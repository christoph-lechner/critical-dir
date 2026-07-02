-- 2026-06-29
-- Modified of doc/schema.sql
-- The names of the tables were changed

-- NOTE: if you change the definition of this table, be sure to update the data ingestion script
CREATE TABLE criticalmaps_data_test(
    _h TEXT,
    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);

-- NOTE: if you change the definition of this table, be sure to update the data ingestion script
-- NOTE: By purpose this table has different name than tables used for operation
CREATE TABLE criticalmaps_stats_test(
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
