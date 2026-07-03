#!/usr/bin/env python3

from pathlib import Path
import jinja2
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--generate', type=str, help='specify what schema to generate')
args = parser.parse_args()

# location of template: same directory as this script
scriptdir = Path(__file__).parent
templateLoader = jinja2.FileSystemLoader(searchpath=scriptdir)
templateEnv = jinja2.Environment(loader=templateLoader)
template = templateEnv.get_template('schema.sql.template')

def generate_main_schema():
    t = template.render(create_indices=True)
    print(t)

def generate_dockeringtest_schema():
    for k in ['_test', '_test_idempotency', '_test_badlat', '_test_badlng']:
        t = template.render(id_project=k)
        print(t)

def generate_dockertest_schema():
    # for test of Docker-based API server image, use standard schema
    generate_main_schema()


if args.generate is None:
    generate_main_schema()
elif args.generate=='docker-ing-test':
    generate_dockeringtest_schema()
elif args.generate=='docker-test':
    generate_dockertest_schema()
else:
    raise ValueError(f'unknown target: {generate}')
