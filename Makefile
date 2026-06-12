.PHONY: help up-api up-all

help:
	echo "Makefile to launch Docker containers"

up-api:
	cd docker_api && docker compose up -d

up-all: up-api

