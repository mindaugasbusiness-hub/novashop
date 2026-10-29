FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

# git/reachable tools, kuriuos Cline naudoja darbui su kodu
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git ripgrep jq python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Cline CLI (headless agentas)
RUN npm install -g cline@latest && cline --version

RUN useradd --create-home --uid 1000 worker \
    && mkdir -p /data/cline /work /app \
    && chown -R worker:worker /data /work /app

COPY server.js /app/server.js

USER worker
ENV PORT=7070 \
    CLINE_CONFIG=/data/cline \
    CLINE_DATA_DIR=/data/cline/data \
    WORKSPACE_ROOT=/work

WORKDIR /work
EXPOSE 7070
CMD ["node", "/app/server.js"]
