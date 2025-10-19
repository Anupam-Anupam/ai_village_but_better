import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'hub'))

from db import Base, engine
from models import *

print("Creating tables in database...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully!")
