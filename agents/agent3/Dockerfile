# Agent 3 Dockerfile - Llama Agent with Shared MongoDB
# ===================================================
# This agent connects to the shared MongoDB instance

FROM python:3.10-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements
COPY agents/shared/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared database models
COPY agents/shared/ ./shared/

# Copy agent-specific files
COPY agents/agent3/agent.py .

# Set environment variables
ENV PYTHONPATH=/app
ENV AGENT_ID=3

# Expose port
EXPOSE 8001

# Run the agent (no MongoDB startup needed)
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]