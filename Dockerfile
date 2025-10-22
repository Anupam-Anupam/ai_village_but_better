FROM python:3.10-slim-bullseye

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY server/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server directory contents
COPY server/ .

# Set environment variables
ENV PYTHONPATH=/app

# Expose the port the agent will run on
EXPOSE 8000

# Command to run the server
CMD ["uvicorn", "router:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]