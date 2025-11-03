from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime

# Database URL - using environment variable with fallback
DATABASE_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://hub:hubpassword@postgres:5432/hub"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class RequestLog(Base):
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    method = Column(String)
    path = Column(String)
    status_code = Column(Integer)
    client_host = Column(String)
    user_agent = Column(String)
    request_headers = Column(JSON)
    request_body = Column(Text, nullable=True)
    response_headers = Column(JSON, nullable=True)
    response_body = Column(Text, nullable=True)
    processing_time = Column(Integer)  # in milliseconds

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)
