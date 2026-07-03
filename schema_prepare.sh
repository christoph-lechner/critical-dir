#!/usr/bin/env bash

set -xe

src/schema/schema_generator.py > doc/schema.sql
src/schema/schema_generator.py --generate=docker-ing-test > tests/docker/testdata-ing_pg/100-schema-autogen.sql
src/schema/schema_generator.py --generate=docker-test > tests/docker/testdata_pg/010-schema.sql
