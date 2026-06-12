When the database is first created, the `postgres` Docker image automatically processes all `.sql` and `.sh` files found in directory `/docker-entrypoint-initdb.d/`, a process called pre-seeding. https://docs.docker.com/guides/pre-seeding/

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

The test data was generated using the command:
```
(venv_scratch) cl@clpc:~/work/criticalmaps--richtungspfeil/.github/workflows/testdata_pg$ ../../../scripts/generate_sql_testdata.py > 002-testdata.sql
```
In the future, this should be automatized

## Manual development/testing of the process
While developing this process, the following commands were used (no `docker compose up` is issues):
```
docker compose -f docker-compose.ci.yml build

# also starts depending services (they continue to run)
docker compose -f docker-compose.ci.yml run --rm tests

docker compose -f docker-compose.ci.yml down -v
```

