# Tests: Overview
## Tests with `pytest`
The tests implemented with `pytest` are relatively lightweight and therefore run in the GitHub Actions environment on every push to any branch.

An important subset of these tests requires a PostgreSQL database to verify data manipulation functions used in the ingestion pipeline.
For local testing on your machine, these tests are skipped by default (because they require access to a running PostgreSQL server). 
Set the environment variable `TESTS_PG_DSN` to enable these tests. This variable is set for the tests in the GitHub Actions environment in this repository.

## Docker-based Tests
Pushes to the `master` branch trigger an additional, more extensive workflow implemented in GitHub Actions. As detailed on the respective pages, it is possible and highly recommended to run the tests on your local machine before pushing the code to the repository.

Currently, two Docker-based suites of tests are available. They are described in more detail here:
- Tests of the [API server](docker/)
- Tests of the [data ingestion process](docker-ing/)
