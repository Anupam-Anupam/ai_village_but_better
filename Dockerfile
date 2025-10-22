FROM python:3.10-slim-bullseye

WORKDIR /app

# Copy and install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server's source code into the container
COPY server/router.py .
COPY server/task_parser.py .
COPY server/requirements.txt .
COPY .env .

# Expose the port the server will run on
EXPOSE 8000

# Command to run the server
CMD ["uvicorn", "router:app", "--host", "0.0.0.0", "--port", "8000"]