
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from backend.database import Base

class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String)
    agent_name = Column(String)
    action = Column(Text)
    status = Column(String)
    metadata_ = Column("metadata", JSON) # 'metadata' is reserved in SQLAlchemy Base
    langfuse_trace_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
