# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for the agent
RUN apt-get update && apt-get install -y \
    # Basic utilities
    curl \
    wget \
    git \
    # Essential libraries for computer vision
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    # For image processing
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    # For font rendering (useful for screenshots)
    fonts-dejavu-core \
    fonts-liberation \
    # For web browsing capabilities
    xvfb \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DISPLAY=:99

# Copy project files
COPY pyproject.toml ./
COPY requirements.txt ./
COPY main.py ./
COPY utils.py ./
COPY README.md ./

# Install Python dependencies
# First install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Install project dependencies using uv
RUN uv pip install --system --no-cache-dir -e .

# Create directories for trajectories and logs
RUN mkdir -p trajectories logs

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash agent && \
    chown -R agent:agent /app
USER agent

# Expose port (if needed for web interface)
EXPOSE 8000

# Set default command
CMD ["python", "main.py"]
