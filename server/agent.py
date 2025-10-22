import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from datetime import datetime

# Import database models and functions
from db import get_db, RequestLog, init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from a .env file at startup
load_dotenv()

# --- CONFIGURATION ---
# The API key is passed via environment variable for security
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found. Please set it in your .env file or as an environment variable.")

# Initialize database
init_db()

# Initialize OpenAI client
client = OpenAI(api_key=API_KEY)

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def log_request(db: Session, input_text: str, response: str = None, error: str = None):
    """Log a request to the database."""
    try:
        log = RequestLog(
            input_text=input_text,
            response=response,
            status="error" if error else "success",
            error_message=error
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    except Exception as e:
        logger.error(f"Error logging request: {str(e)}")
        db.rollback()
        raise

@app.post("/execute")
async def execute_task(req: Request, db: Session = Depends(get_db)):
    """
    Receives a task, sends it to the GPT-4 API, logs the request, and returns the result.
    """
    task_payload = await req.json()
    input_text = task_payload.get("input_text", "")
    
    try:
        # Call the OpenAI API
        completion = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Answer the user's question directly and concisely."},
                {"role": "user", "content": input_text}
            ]
        )
        
        # Get the response content
        response_content = completion.choices[0].message.content
        
        # Log the successful request
        log_request(db, input_text, response_content)
        
        return {"response": response_content}
        
    except Exception as e:
        # Log the error
        error_message = str(e)
        try:
            log_request(db, input_text, error=error_message)
        except Exception as log_error:
            logger.error(f"Failed to log error: {log_error}")
        
        raise HTTPException(status_code=500, detail=error_message)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}