from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Facility(Base):
    __tablename__ = "facilities"

    id = Column(String, primary_key=True, default=generate_uuid)
    raw_id = Column(String, nullable=True, index=True) # ID from the file
    
    # Basic Info
    name = Column(String, index=True)
    sehir = Column(String, index=True) # Renamed from city
    ilce = Column(String, index=True)  # Renamed from district
    type = Column(String, index=True) # Belge Turu
    address = Column(String, nullable=True)
    
    # Discovery Data
    website = Column(String, nullable=True)
    website_source = Column(String, nullable=True) # 'ddg', 'manual'
    website_score = Column(Float, default=0.0) # Confidence score
    website_status = Column(String, default="pending") # pending, found, not_found
    
    # Email Data
    email = Column(String, nullable=True)
    email_source = Column(String, nullable=True) # 'homepage', 'contact_page', 'mailto'
    email_status = Column(String, default="pending") # pending, found, not_found

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_type = Column(String) # 'discovery', 'email_crawl'
    status = Column(String, default="queued") # queued, running, completed, failed
    
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")

class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id"))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    level = Column(String) # INFO, ERROR, WARNING, SUCCESS
    message = Column(Text)
    
    job = relationship("Job", back_populates="logs")
