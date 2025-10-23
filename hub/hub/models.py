from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from db import Base

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    container_id = Column(String(100))  # Docker container ID
    memory_window_size = Column(Integer, default=10)  # Number of memories to keep
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    tasks = relationship("Task", back_populates="agent")
    memories = relationship("Memory", back_populates="agent")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), index=True)
    description = Column(Text)
    input_data = Column(JSON)  # Input data for the agent
    output_data = Column(JSON)  # Output from the agent
    status = Column(String(50), default="pending")  # pending, in_progress, completed, failed
    agent_id = Column(Integer, ForeignKey("agents.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="tasks")

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    memory_type = Column(String(50), default="general")  # general, task_result, observation
    agent_id = Column(Integer, ForeignKey("agents.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    agent = relationship("Agent", back_populates="memories")
