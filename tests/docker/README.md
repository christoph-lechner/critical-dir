# README.md
This directory contains tests that are used to verify that the API server runs after building the Docker image.
After building the image, the tests are executed **in the directory layout of the image** with `pytest`.

**Table of contents**
- Manual development/testing of the process
- Debugging
- Technical remarks

## Manual development/testing of the process
While developing this process, the commands listed below were used (no `docker compose up` is issued, all commands are executed in the top directory of the project/repository). These commands can also be used to test any changes to the code before pushing to Github.
```
docker compose -f ./tests/docker/docker-compose.ci.yml build

# also starts depending services (they continue to run)
docker compose -f ./tests/docker/docker-compose.ci.yml run --rm tests

docker compose -f ./tests/docker/docker-compose.ci.yml down -v
```
## Debugging
If you need to debug this test setup, you can launch the containers
```
docker compose -f ./tests/docker/docker-compose.ci.yml up
```
and do the needed debugging. Keep in mind that the timestamps of the entries in the test database are only adjusted at start-up time, so they are only good for a few minutes.

### Running pytest
One thing you can do is manually running `pytest` outside of your container on the console. For instance in the root of the cloned repository:
```
pytest tests/docker/
```
This allows to interactively debug the tests.

### Inspecting the DB
Furthermore, if needed you can inspect the contents of the DB.
Connect to the container running the postgres DB (use `docker ps` to determine the hex id string as there might be multiple) and have a look into the DB:
```
cl@clpc:/tmp$ docker exec -it debf82e89320 /bin/bash
root@debf82e89320:/# psql -h localhost -U testuser testdb
psql (18.4 (Debian 18.4-1.pgdg13+1))
Type "help" for help.

testdb=# \d
               List of relations
 Schema |       Name        | Type  |  Owner   
--------+-------------------+-------+----------
 public | criticalmaps_data | table | testuser
(1 row)

testdb=# SELECT * FROM criticalmaps_data;
[..]
testdb=#
```

### Checking logs
If you wish to see the logs of the previous run, use
```
docker compose -f ./tests/docker/docker-compose.ci.yml logs cdir_api_server
```


## Technical remarks
### Database init
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

### Inspect storage consumed by Docker
When building and running many Docker images on your development system, free disk space might go down.
The amount of storage space consumed by Docker caches etc. might be surprising.
To check (and release some if needed):
```
docker system df

# to release space
# docker builder prune
```
