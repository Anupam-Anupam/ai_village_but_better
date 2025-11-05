FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (add more here if your agent requires them)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency metadata first for better build caching
COPY requirements.txt pyproject.toml ./

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the remaining application code
COPY main.py utils.py ./
# Include trajectories or other data only if you need them inside the image.

# Default command. Override with `docker run ... python other_script.py` if needed.
CMD ["python", "main.py"]

