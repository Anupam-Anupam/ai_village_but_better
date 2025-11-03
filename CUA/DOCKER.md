# Docker Setup for CUA Agent Template

This document explains how to run the CUA Agent Template using Docker.

## Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier management)
- CUA API credentials

## Quick Start

### 1. Environment Setup

Create a `.env` file in the project root with your credentials:

```bash
# Required environment variables
CUA_API_KEY=your_cua_api_key_here
CUA_SANDBOX_NAME=your_sandbox_name_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 2. Build and Run

#### Option A: Using Docker directly

```bash
# Build the image
docker build -t cua-agent-template .

# Run the container
docker run --env-file .env -v $(pwd)/trajectories:/app/trajectories cua-agent-template
```

#### Option B: Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CUA_API_KEY` | Yes | Your CUA API key |
| `CUA_SANDBOX_NAME` | Yes | Name of your CUA sandbox |
| `OPENAI_API_KEY` | Yes | Your OpenAI API key |
| `DISPLAY` | No | X11 display (default: :99) |

### Volume Mounts

- `./trajectories:/app/trajectories` - Persists trajectory data
- `./logs:/app/logs` - Persists log files
- `./.env:/app/.env:ro` - Mounts environment file (read-only)

## Development

### Building for Development

```bash
# Build with no cache
docker build --no-cache -t cua-agent-template .

# Build with specific tag
docker build -t cua-agent-template:latest .
```

### Running with Live Code Changes

```bash
# Mount source code for development
docker run --env-file .env \
  -v $(pwd)/main.py:/app/main.py \
  -v $(pwd)/utils.py:/app/utils.py \
  -v $(pwd)/trajectories:/app/trajectories \
  cua-agent-template
```

### Debugging

```bash
# Run with interactive shell
docker run -it --env-file .env cua-agent-template /bin/bash

# Run with Python debugger
docker run --env-file .env cua-agent-template python -m pdb main.py
```

## Troubleshooting

### Common Issues

1. **Permission denied errors**
   ```bash
   # Fix ownership of mounted volumes
   sudo chown -R $USER:$USER trajectories/ logs/
   ```

2. **Environment variables not loaded**
   ```bash
   # Check if .env file exists and has correct format
   cat .env
   
   # Test environment loading
   docker run --env-file .env cua-agent-template env | grep CUA
   ```

3. **GUI/X11 issues**
   ```bash
   # Enable X11 forwarding (Linux/macOS)
   xhost +local:docker
   
   # Or use the GUI profile with docker-compose
   docker-compose --profile gui up
   ```

4. **Out of memory errors**
   ```bash
   # Increase Docker memory limit in Docker Desktop settings
   # Or run with memory limit
   docker run --memory=4g --env-file .env cua-agent-template
   ```

### Logs and Debugging

```bash
# View container logs
docker logs cua-agent-template

# Follow logs in real-time
docker logs -f cua-agent-template

# Execute commands in running container
docker exec -it cua-agent-template /bin/bash

# Check container resource usage
docker stats cua-agent-template
```

## Production Deployment

### Security Considerations

1. **Use secrets management** instead of .env files
2. **Run as non-root user** (already configured)
3. **Use read-only filesystem** where possible
4. **Limit container resources**

### Example Production Setup

```bash
# Build production image
docker build -t cua-agent-template:prod .

# Run with resource limits
docker run -d \
  --name cua-agent-prod \
  --memory=2g \
  --cpus=1.0 \
  --restart=unless-stopped \
  --env-file .env \
  -v /data/trajectories:/app/trajectories \
  cua-agent-template:prod
```

### Health Checks

Add health check to Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
```

## Advanced Usage

### Multi-stage Build

For smaller production images, use multi-stage builds:

```dockerfile
# Build stage
FROM python:3.12-slim as builder
WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir uv && uv pip install --system --no-cache-dir -e .

# Runtime stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY main.py utils.py ./
CMD ["python", "main.py"]
```

### Custom Entrypoint

Create a custom entrypoint script:

```bash
#!/bin/bash
set -e

# Wait for dependencies
echo "Waiting for CUA services..."
sleep 10

# Run the application
exec "$@"
```

Then in Dockerfile:
```dockerfile
COPY entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["entrypoint.sh"]
CMD ["python", "main.py"]
```
