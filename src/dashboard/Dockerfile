# based on https://docs.streamlit.io/deploy/tutorials/docker

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*
# CL: removed line to install package software-properties-common

RUN pip3 install streamlit numpy pandas plotly
RUN pip3 install "psycopg[binary,pool]"
RUN pip3 install pydantic pydantic_settings

# CL: run streamlit as user with reduced privileges (need to generate directory and adjust privileges)
RUN groupadd -r appgroup && useradd -r -g appgroup -u 999 appuser
RUN mkdir /.streamlit
RUN chown appuser /.streamlit

USER appuser:appgroup

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]

