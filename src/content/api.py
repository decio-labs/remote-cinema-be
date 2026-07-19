from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from src.config.database import get_db
from .schemas import ContentResponse, UserLibraryResponse
from src.services.helpers.dependencies import get_current_user
from src.content.services import upload_content, library
from src.models.users.auth import UserModel

router = APIRouter(prefix="/content", tags=["content"])

@router.post("/upload", response_model=ContentResponse)
async def upload_content_endpoint(
    title: str,
    description: str,
    duration: float,
    file: UploadFile = File(), 
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    return await upload_content(file, title, description, duration, current_user.user_id, db)

@router.get("/library", status_code=200, response_model=UserLibraryResponse)
async def user_library(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await library(current_user.user_id, db)