# README.md
This directory contains tests that are used to verify that the API server runs after building the Docker image.
After building the image, the tests are executed **in the directory layout of the image** with `pytest`.

## Manual development/testing of the process
While developing this process, the commands listed below were used (no `docker compose up` is issued, all commands are executed in the top directory of the project/repository). These commands can also be used to test any changes to the code before pushing to Github.
```
docker compose -f ./tests_docker/docker-compose.ci.yml build

# also starts depending services (they continue to run)
docker compose -f ./tests_docker/docker-compose.ci.yml run --rm tests

docker compose -f ./tests_docker/docker-compose.ci.yml down -v
```

If you wish to see the logs of the previous run, use
```
docker compose -f ./tests_docker/docker-compose.ci.yml logs cdir_api_server
```


## Technical remarks
When the database is first created, the `postgres` Docker image automatically processes all `.sql` and `.sh` files found in directory `/docker-entrypoint-initdb.d/`, a process called [pre-seeding](https://docs.docker.com/guides/pre-seeding/).

When everything worked, you see at the first start-up of the DB in the output:
```
[..]
pgdatabase-1  | /usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/001-schema.sql
pgdatabase-1  | CREATE TABLE
pgdatabase-1  | CREATE INDEX
pgdatabase-1  | CREATE INDEX
pgdatabase-1  | CREATE INDEX
[..]
```

The test data in file `020-testdata.sql` was generated using the command `scripts/generate_sql_testdata.py`. In the future, this should be automatized.

In addition a few more `.sql` files are needed to fully prepare the database for the test of the clustering algorithm.

