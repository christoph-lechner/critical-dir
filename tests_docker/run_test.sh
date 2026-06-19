#!/bin/bash

# Helper script for manual evaluation of status as part of
# "git bisect" procedure. Automatic launch directly from
# "git bisect" has not been tested
#
# Be sure to check free disk space.

docker compose -f ./tests_docker/docker-compose.ci.yml build

docker compose -f ./tests_docker/docker-compose.ci.yml run --rm tests
STATUS_TEST=$?

docker compose -f ./tests_docker/docker-compose.ci.yml down --rmi all

echo "status is: $STATUS_TEST"
exit $STATUS_TEST
