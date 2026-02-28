
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, UniqueConstraint
from datetime import datetime
from backend.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String)
    platform = Column(String)
    job_url = Column(String)
    description = Column(Text)
    match_score = Column(Float)
    hr_email = Column(String)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('company', 'title', 'location', name='uq_job_company_title_location'),
    )
