import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'hub'))

from db import Base, engine, SessionLocal
from models import *

print("Creating tables in database...")
Base.metadata.create_all(bind=engine)

# Create sample agents
db = SessionLocal()
try:
    # Check if agents already exist
    existing_agents = db.query(Agent).count()
    if existing_agents == 0:
        print("Creating sample agents...")
        
        agent1 = Agent(
            name="Research Agent",
            description="AI agent specialized in research tasks",
            is_active=True,
            memory_window_size=10
        )
        
        agent2 = Agent(
            name="Analysis Agent", 
            description="AI agent specialized in data analysis",
            is_active=True,
            memory_window_size=15
        )
        
        db.add(agent1)
        db.add(agent2)
        db.commit()
        
        print("✅ Sample agents created!")
    else:
        print("✅ Agents already exist, skipping creation")
        
finally:
    db.close()

print("✅ Database initialization complete!")
