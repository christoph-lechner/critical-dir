

-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats_test(
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
CREATE TABLE criticalmaps_data_test (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine_test (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);





-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats_test_idempotency(
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
CREATE TABLE criticalmaps_data_test_idempotency (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_idempotency(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine_test_idempotency (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_idempotency(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);





-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats_test_badlat(
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
CREATE TABLE criticalmaps_data_test_badlat (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badlat(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine_test_badlat (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badlat(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);





-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats_test_badlng(
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
CREATE TABLE criticalmaps_data_test_badlng (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badlng(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine_test_badlng (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badlng(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);





-------------------------------------------------------------
-- Generated from template using jinja.                    --
--                                                         --
-- Don't modify this file. Instead modify the template and --
-- re-run generation script.                               --
-------------------------------------------------------------

-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_stats_test_badurl(
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
CREATE TABLE criticalmaps_data_test_badurl (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badurl(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);


-- NOTE: if you change the definition of this table, be sure to update
-- the data ingestion script
CREATE TABLE criticalmaps_data_quarantine_test_badurl (
    _h TEXT,
    -- NOTE: there is no "NOT NULL" in the following row definition, so "NULL" satisfies the constraint
    id_run BIGINT REFERENCES criticalmaps_stats_test_badurl(id),

    deviceid TEXT,
    latitude FLOAT,
    longitude FLOAT,
    timestamp INT,
    ts_entry_creation TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (_h)
);



