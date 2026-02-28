
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
import shutil
import os
import logging
from datetime import datetime
import json

from backend.database import get_db
from backend.models.cv_version import CVVersion
# Import correctly from backend - check that the file exists and is importable
# Assuming backend is a module (has __init__.py)
from backend.agents.cv_parser_agent import extract_text_from_pdf, extract_text_from_docx, cv_parser_node
from backend.agents.state import HirePilotState

# Configure logging for this module
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(tags=["CV"])

UPLOAD_DIR = "data/uploads"
# Ensure the directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads a CV file (PDF or DOCX), extracts text, parses it using the AI agent,
    and stores the result in the database.
    """
    try:
        # 1. Save file to disk
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File uploaded to {file_path}")

        # 2. Extract Text
        content_type = file.content_type
        # Simple extension check as fallback
        filename = file.filename.lower()
        
        cv_text = ""
        try:
            if filename.endswith(".pdf"):
                cv_text = extract_text_from_pdf(file_path)
            elif filename.endswith(".docx") or filename.endswith(".doc"):
                cv_text = extract_text_from_docx(file_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX.")
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

        if not cv_text or not cv_text.strip():
             raise HTTPException(status_code=400, detail="Could not extract text from file (empty content).")

        # 3. Parse with AI Agent
        # Create a minimal state for the agent
        # We manually invoke the node function here as a utility
        state = {
            "user_message": "Parse this CV",
            "thread_id": f"upload_{datetime.now().timestamp()}",
            "cv_text": cv_text,
            "cv_structured": None,
            "job_search_criteria": None,
            "found_jobs": [],
            "hitl_approved": False,
            # Add other required keys if any, check state definition
        }
        
        # Check cv_parser_node signature: (state: HirePilotState) -> HirePilotState
        updated_state = cv_parser_node(state)
        parsed_data = updated_state.get("cv_structured")

        if not parsed_data:
            # Fallback or error?
            logger.error("AI parsing returned no data.")
            raise HTTPException(status_code=500, detail="AI parsing failed to return structured data.")

        # 4. Save to Database
        new_cv = CVVersion(
            filename=file.filename,
            raw_text=cv_text,
            parsed_data=parsed_data,
            created_at=datetime.utcnow()
        )
        db.add(new_cv)
        db.commit()
        db.refresh(new_cv)

        # 5. Return Response
        skills = parsed_data.get("skills", [])
        skills_count = len(skills) if skills else 0
        
        return {
            "cv_id": new_cv.id,
            "filename": new_cv.filename,
            "parsed_cv": parsed_data,
            "skills_count": skills_count,
            "message": "CV uploaded and parsed successfully"
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error processing upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/versions")
def get_cv_versions(db: Session = Depends(get_db)):
    """
    Returns all CV versions ordered by creation date descending.
    """
    versions = db.query(CVVersion).order_by(desc(CVVersion.created_at)).all()
    return versions
