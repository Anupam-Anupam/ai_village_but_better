FROM python:3.10-slim-bullseye

WORKDIR /app

# Copy and install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the agent's source code into the container
COPY docker/agent.py .
COPY .env .

# Expose the port the agent will run on (as defined in router.py)
EXPOSE 8001

# Command to run the agent server
# --host 0.0.0.0 makes it accessible from outside the container
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]