# reset_db.py
import os
import sys

# Add the current directory to sys.path so we can import 'app'
sys.path.append(os.path.abspath(os.getcwd()))

from app.db.session import engine, Base
from app import models

def reset():
    print("⏳ Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ Tables dropped.")
    
    print("⏳ Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully with new schema.")

if __name__ == "__main__":
    reset()
