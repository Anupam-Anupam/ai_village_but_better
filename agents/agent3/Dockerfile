# Agent 3 Dockerfile - Llama Agent with Embedded MongoDB
# =====================================================
# This creates a self-contained agent container with:
# - Python 3.10 runtime
# - Embedded MongoDB database (agent3db)
# - FastAPI web server
# - Llama AI integration
# - Complete isolation from other agents

FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies including MongoDB
# This installs MongoDB directly in the container for embedded database
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    wget \
    gnupg \
    && wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/debian bullseye/mongodb-org/7.0 main" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list \
    && apt-get update \
    && apt-get install -y mongodb-org \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements first (for better Docker layer caching)
COPY agents/shared/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared database models and utilities
# This provides the AgentDatabase class for MongoDB operations
COPY agents/shared/ ./shared/

# Copy agent-specific files
COPY agents/agent3/agent.py .
COPY .env .

# Set environment variables
ENV PYTHONPATH=/app
ENV AGENT_ID=3

# Create MongoDB data directory
# This is where the agent's embedded MongoDB will store data
RUN mkdir -p /data/db

# Expose the port the agent will run on
EXPOSE 8001

# Start MongoDB and run agent
# This starts the embedded MongoDB instance and then the FastAPI server
# Each agent gets its own MongoDB instance running on localhost:27017
CMD ["sh", "-c", "mongod --dbpath /data/db --bind_ip_all --fork --logpath /var/log/mongodb.log && uvicorn agent:app --host 0.0.0.0 --port 8001"]