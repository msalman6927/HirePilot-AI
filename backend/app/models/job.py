import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job_matches: Mapped[list["JobMatch"]] = relationship(  # noqa: F821
        "JobMatch", back_populates="job", cascade="all, delete-orphan"
    )
    customized_resumes: Mapped[list["CustomizedResume"]] = relationship(  # noqa: F821
        "CustomizedResume", back_populates="job", cascade="all, delete-orphan"
    )
    outreach_emails: Mapped[list["OutreachEmail"]] = relationship(  # noqa: F821
        "OutreachEmail", back_populates="job", cascade="all, delete-orphan"
    )
