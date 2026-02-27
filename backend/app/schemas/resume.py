import datetime

from pydantic import BaseModel


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_path: str
    content_type: str
    uploaded_at: datetime.datetime

    model_config = {"from_attributes": True}
