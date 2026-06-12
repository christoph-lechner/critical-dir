-- Data analysis procedure only takes recent data into account.
-- Adjust timestamp of test data.
UPDATE criticalmaps_data SET timestamp=EXTRACT(EPOCH FROM NOW());
