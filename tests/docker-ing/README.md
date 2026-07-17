This directory contains the `pytest` input files for **evaluating** the tests of ingestion process using Docker.
The corresponding docker-compose file is currently stored in a different directory, as are the files needed to prepare the SQL DB for the tests.
(There are also tests of some important data manipulation steps using `pytest`, they are described elsewhere.)


## Steps
- Prepare database using schema.
  - The schema describes independent copies of the tables for multiple tests (just cloning them using `SELECT * INTO ...` would not work because of the foreign key constrains)
- Run the Docker container multiple times, with different input arguments
- Examine the resulting tables using `pytest`.

## Tests
The functions in `test_ing.py` evaluate the data stored in the various database tables after running the Docker "image under test" multiple times.

### Test 1
Performs ingestion of a known dataset (provided using `file://` URL).

### Test 2
Perform test for idempotence.
Run the same Docker image twice using identical input data (provided using `file://` URL), then examine the result.
As a PostgreSQL DB has to be prepared for this test on a GitHub runner (the idempotence is the result of a `MERGE` operation), using `docker compose` appears to be a reasonable solution.

### Test 3
Test with bad latitude and longitude value, respectively.
In each case, one device update is routed to quarantine table. All other device updates are stored in the "normal" data table.

### Test 4
Tests reaction to issues with API requests.
For the test to pass, there has to be a single entry in the table informing us about the type of exception and further details.

## Useful commands
(See also [../docker/README.md](here) for more infos)
```
docker compose -f ./tests/docker/docker-compose.ci-ingest.yml build
docker compose -f ./tests/docker/docker-compose.ci-ingest.yml run --rm tests

# if needed, you can inspect the database contents here

docker compose -f ./tests/docker/docker-compose.ci-ingest.yml down -v
```
