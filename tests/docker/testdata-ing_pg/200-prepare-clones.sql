-- Prepare empty tables for idempotency test
SELECT * INTO criticalmaps_data_test_idempotency FROM criticalmaps_data_test;
SELECT * INTO criticalmaps_stats_test_idempotency FROM criticalmaps_stats_test;

-- Test with bad lat/lng
SELECT * INTO criticalmaps_data_test_badlat FROM criticalmaps_data_test;
SELECT * INTO criticalmaps_stats_test_badlat FROM criticalmaps_stats_test;
SELECT * INTO criticalmaps_data_test_badlng FROM criticalmaps_data_test;
SELECT * INTO criticalmaps_stats_test_badlng FROM criticalmaps_stats_test;
