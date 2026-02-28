
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def placeholder():
    return {"status": "placeholder", "module": "prep"}
