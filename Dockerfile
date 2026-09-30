FROM apache/airflow:3.3.2

COPY --from=ghcr.io/astral-sh/uv:0.12.15 /uv /usr/local/bin/uv

WORKDIR /opt/airflow

USER root
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN chown -R airflow: pyproject.toml uv.lock src
USER airflow

RUN uv pip install --no-cache .
