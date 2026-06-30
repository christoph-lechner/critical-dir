This directory contains the `pytest` input files for testing the ingestion process using Docker.
The corresponding docker-compose file is currently stored in a different directory, as are the files needed to prepare the SQL DB for the tests.

## Preparations
- Prepare database using schema.
- Prepare independent copies of tables for multiple tests

## Tests
### Test 1
Performs ingestion of a known dataset (provided using `file://` URL).

### Test 2
Perform test for idempotence.
Run the same Docker image twice using identical input data (provided using `file://` URL), then examine the result.
As a PostgreSQL DB has to be prepared for this test on a GitHub runner (the idempotence is the result of a `MERGE` operation), using `docker compose` appears to be a reasonable solution.


## Useful commands
```
docker compose -f ./tests/docker/docker-compose.ci-ingest.yml build
docker compose -f ./tests/docker/docker-compose.ci-ingest.yml run --rm tests
docker compose -f ./tests/docker/docker-compose.ci-ingest.yml down -v
```
