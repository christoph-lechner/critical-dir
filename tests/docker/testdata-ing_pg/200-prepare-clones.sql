-- Prepare empty tables for idempotency test
SELECT * INTO criticalmaps_data_test_idempotency FROM criticalmaps_data_test;
CREATE TABLE criticalmaps_stats_test_idempotency (LIKE criticalmaps_stats_test INCLUDING ALL);

-- Test with bad lat/lng
SELECT * INTO criticalmaps_data_test_badlat FROM criticalmaps_data_test;
CREATE TABLE criticalmaps_stats_test_badlat (LIKE criticalmaps_stats_test INCLUDING ALL);
SELECT * INTO criticalmaps_data_test_badlng FROM criticalmaps_data_test;
CREATE TABLE criticalmaps_stats_test_badlng (LIKE criticalmaps_stats_test INCLUDING ALL);
