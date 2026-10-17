# serves only the v1 /system app, with git installed and no credentials baked in

FROM python:3.12-slim

# installs git, the connector's only tool, and nothing else
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY Source/ Source/

# runs as an unprivileged user that owns the run store
RUN useradd --create-home --uid 10001 drifter && mkdir -p /app/runs && chown drifter /app/runs
USER drifter

# names the build in every run file, set at build time from the commit
ARG TOOL_VERSION=1.1.0
ENV DRIFTER_TOOL_VERSION=${TOOL_VERSION} \
    DRIFTER_RUNS_DIR=/app/runs \
    PYTHONUNBUFFERED=1

# listens on Render's PORT, 8000 when run locally
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn --app-dir Source GitHub_Connector.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
