import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="resumes")  # noqa: F821
    parsed_profile: Mapped["ParsedProfile"] = relationship(  # noqa: F821
        "ParsedProfile", back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )
    customized_resumes: Mapped[list["CustomizedResume"]] = relationship(  # noqa: F821
        "CustomizedResume", back_populates="resume", cascade="all, delete-orphan"
    )
