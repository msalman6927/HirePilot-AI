from sqlalchemy.orm import Session

from app.models.resume import Resume


def get_resume(db: Session, resume_id: int) -> Resume | None:
    return db.query(Resume).filter(Resume.id == resume_id).first()


def get_resumes_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Resume]:
    return db.query(Resume).filter(Resume.user_id == user_id).offset(skip).limit(limit).all()


def create_resume(db: Session, user_id: int, filename: str, file_path: str, content_type: str) -> Resume:
    db_resume = Resume(
        user_id=user_id,
        filename=filename,
        file_path=file_path,
        content_type=content_type,
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return db_resume


def delete_resume(db: Session, resume: Resume) -> None:
    db.delete(resume)
    db.commit()
