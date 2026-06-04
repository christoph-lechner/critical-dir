FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
# CL: removed line to install package software-properties-common

# TODO: replace by git clone from github
COPY . /app
RUN rm /app/.env

RUN pip3 install --no-cache-dir --upgrade pip
RUN pip3 install --no-cache-dir -e .

# CL: run as user with reduced privileges
RUN groupadd -r appgroup && useradd -r -g appgroup -u 999 appuser

USER appuser:appgroup

EXPOSE 8080

HEALTHCHECK --interval=1m --start-period=5m \
	CMD curl --fail http://localhost:8080/check || exit 1

ENTRYPOINT ["critical-dir-apiimport", "--status_port=8080"]
