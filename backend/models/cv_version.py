
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from backend.database import Base

class CVVersion(Base):
    __tablename__ = "cv_versions"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String)
    raw_text = Column(Text)
    parsed_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
