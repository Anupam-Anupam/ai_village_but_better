import time
from fastapi import Request
from fastapi.responses import Response
from contextlib import asynccontextmanager
from ..db import RequestLog, SessionLocal
import json

@asynccontextmanager
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Read request body
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        request_body = await request.body()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = int((time.time() - start_time) * 1000)
    
    # Log to database
    db = SessionLocal()
    try:
        log = RequestLog(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            client_host=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_headers=dict(request.headers),
            request_body=request_body.decode() if request_body else None,
            processing_time=process_time
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error logging request: {e}")
    finally:
        db.close()
    
    return response
