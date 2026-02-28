
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    cv_version_id = Column(Integer, ForeignKey("cv_versions.id"))
    tailored_cv = Column(JSON)
    email_draft = Column(Text)
    hr_email = Column(String)
    sent_at = Column(DateTime)
    status = Column(String, default="Sent")

    job = relationship("Job")
    cv_version = relationship("CVVersion")
