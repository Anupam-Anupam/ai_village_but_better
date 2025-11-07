FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies and create user
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3-venv curl ca-certificates tini \
    # Playwright runtime dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libatspi2.0-0 xvfb libxkbcommon0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && useradd --create-home --shell /bin/bash agent1 \
    && mkdir -p /home/agent1/workdir /app \
    && chown -R agent1:agent1 /home/agent1 /app \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python packages
COPY agents/agent_sandbox/requirements.txt /app/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r /app/requirements.txt

# Install Playwright browsers as root (before switching to non-root user)
RUN python3 -m playwright install --with-deps

# Copy application code and set ownership to non-root user
COPY agents/agent_sandbox/app /app/app
RUN chown -R agent1:agent1 /app

# Set environment variables
ENV PYTHONPATH=/app
ENV AGENT_ID=1
ENV HOME=/home/agent1

# Switch to non-root user
USER agent1
WORKDIR /home/agent1/workdir

EXPOSE 8001

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]