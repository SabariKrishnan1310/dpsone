
import os
import time
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime


DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST")
DB_NAME = os.environ.get("POSTGRES_DB")


SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"


engine = create_engine(SQLALCHEMY_DATABASE_URL)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()


class AttendanceLog(Base):
    __tablename__ = "attendance_log"
    
    log_id = Column(Integer, primary_key=True, index=True)
    rfid_uid = Column(String, index=True, nullable=False)
    
    
    school_id = Column(String, nullable=False, index=True) 
    location = Column(String, nullable=True)             
    role = Column(String, nullable=False, default="STUDENT") 
    current_time = Column(DateTime, default=datetime.utcnow) 
    

    device_id = Column(String, nullable=False)
    status = Column(String, default="IN") 
    timestamp = Column(DateTime, default=datetime.utcnow) 

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    
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
            
    
    Base.metadata.create_all(bind=engine)
    print("AttendanceLog table ensured.")