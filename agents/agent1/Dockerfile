# Dockerfile for a Secure AI Agent Sandbox
# Base Image: Ubuntu 22.04
FROM ubuntu:22.04

# 1. Set up environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 2. Install system dependencies
# - python3 and pip for the application
# - tini as a lightweight init system to handle signals properly
# - System dependencies required by Playwright for browser automation
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    tini \
    # Playwright dependencies
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libatspi2.0-0 \
    libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    && useradd --create-home --shell /bin/bash agent \
    && mkdir -p /home/agent/app /home/agent/workdir \
    && chown -R agent:agent /home/agent \
    && rm -rf /var/lib/apt/lists/*

# 3. Create a non-root user for security
RUN useradd --create-home --shell /bin/bash agent
WORKDIR /home/agent/app

# 4. Install Python dependencies
COPY agents/agent1/requirements.txt /home/agent/app/requirements.txt
RUN python3 -m pip install --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r /home/agent/app/requirements.txt

# 5. Install Playwright browsers
RUN python3 -m playwright install --with-deps

# 6. Copy application code and set permissions
COPY agents/agent1/agent.py /home/agent/app/
COPY agents/shared/ /home/agent/app/shared/
RUN chown -R agent:agent /home/agent/app

ENV PYTHONPATH=/home/agent/app

USER agent
ENV HOME=/home/agent
WORKDIR /home/agent/workdir

# 7. Expose port and define entrypoint
EXPOSE 8001
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]