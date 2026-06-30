-- Prepare empty tables for idempotency test
SELECT * INTO criticalmaps_data_test_idempotency FROM criticalmaps_data_test;
SELECT * INTO criticalmaps_stats_test_idempotency FROM criticalmaps_stats_test;
