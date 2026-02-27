import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ParsedProfile(Base):
    __tablename__ = "parsed_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    skills: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    experience: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    education: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(nullable=True)
    parsed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    resume: Mapped["Resume"] = relationship("Resume", back_populates="parsed_profile")  # noqa: F821
