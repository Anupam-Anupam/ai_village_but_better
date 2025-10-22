FROM python:3.10-slim-bullseye

# Setup Python Environment
WORKDIR /app
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Agent Script
COPY server/agent.py .
COPY .env .

# Expose the port the agent will run on
EXPOSE 8001

# Command to run the agent server
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8001"]