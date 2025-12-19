# service_ingestion/database.py
import os
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# --- Environment Setup (Reads from docker-compose) ---
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST")
DB_NAME = os.environ.get("POSTGRES_DB")

# Database URL for SQLAlchemy
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# 1. Engine Creation
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 2. Session Setup
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Base Class for ORM Models
Base = declarative_base()

# 4. Table Model (The Attendance Log)
class AttendanceLog(Base):
    __tablename__ = "attendance_log"
    
    log_id = Column(Integer, primary_key=True, index=True)
    rfid_uid = Column(String, index=True, nullable=False)
    
    # --- NEW FIELDS ADDED ---
    school_id = Column(String, nullable=False, index=True) # Identifier for the school (e.g., "DPS_001")
    location = Column(String, nullable=True)             # User-friendly name (e.g., "Main Gate")
    role = Column(String, nullable=False, default="STUDENT") # STUDENT or STAFF
    current_time = Column(DateTime, default=datetime.utcnow) # This will store the time the DEVICE sent the tap
    # ------------------------

    device_id = Column(String, nullable=False)
    status = Column(String, default="IN") 
    timestamp = Column(DateTime, default=datetime.utcnow) # This remains the DB insertion time
# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Function to ensure DB connection and create tables
def create_tables():
    # Wait for the DB service to be fully ready
    print("Attempting to connect to PostgreSQL...")
    connected = False
    max_retries = 10
    retry_count = 0
    while not connected and retry_count < max_retries:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print("PostgreSQL connection successful.")
            connected = True
        except Exception:
            retry_count += 1
            print(f"Connection failed, retrying in 3 seconds... (Attempt {retry_count}/{max_retries})")
            time.sleep(3)
            
    if not connected:
        raise Exception("Could not connect to PostgreSQL database after multiple retries.")
            
    # Create tables defined in the Base class
    Base.metadata.create_all(bind=engine)
    print("AttendanceLog table ensured.")