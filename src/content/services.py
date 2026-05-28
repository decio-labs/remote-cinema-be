import mimetypes
import uuid
from fastapi import HTTPException, HTTPException, UploadFile

from src.config.settings import get_settings
from src.services.users.user_service import user_service
from src.content.storage import stream_upload_to_r2
from src.content.crud import content_service
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .schemas import ContentResponse, UserLibraryResponse
from .models import ContentType, Content
import logging

logger = logging.getLogger("uvicorn.error")

async def  get_file_size_mb(file: UploadFile) -> float: 
    file.file.seek(0, 2)  
    file_size_bytes = file.file.tell()
    file.file.seek(0) 

    # 2. Convert to Megabytes
    file_size_mb = file_size_bytes / (1024 * 1024)

    return file_size_mb

async def upload_content(file: UploadFile, title: str, description: str, duration: float, user_id: uuid.UUID, db: AsyncSession):

    allowed_mime_types = get_settings().VIDEO_MIME_TYPES.values()
    if file.content_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    mime_type, _ = mimetypes.guess_type(file.filename)
    if mime_type not in allowed_mime_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    # Generate a unique key for the file in R2
    file_extension = mimetypes.guess_extension(mime_type) or ''
    unique_key = f"{uuid.uuid4()}{file_extension}"

    public_url = f"{get_settings().CLOUDFLARE_R2_PUBLIC_URL}/{unique_key}"

    # validate file bytes against user subscription limits.
    storage_limit_mb, _= await user_service(db).check_active_user_subscription(user_id)
    if storage_limit_mb is None:
        raise HTTPException(status_code=403, detail="No active subscription found. Please subscribe to a plan to upload content.")
    file_size_mb = await get_file_size_mb(file)
    logger.info(f"File size: {file_size_mb} MB, Storage limit: {storage_limit_mb} MB")

    if file_size_mb > storage_limit_mb:
        raise HTTPException(status_code=403, detail=f"File size exceeds your subscription storage limit of {storage_limit_mb} MB. Please upgrade your plan to upload larger files.")
    
    try:
        file_size_bytes = await stream_upload_to_r2(file, unique_key, mime_type)
        logger.info(f"Uploaded file size: {file_size_bytes} bytes")

    except Exception as e:
        logger.error(f"Failed to upload file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
    
    thumbnail_url = f"{get_settings().THUMBNAIL_GENERATION_SERVICE_URL}?video_url={public_url}"
    
    content = await content_service(db).save_content(
        title=title, description=description,
        content_type=ContentType.VIDEO, r2_key=unique_key,
        url=public_url, thumbnail_url=thumbnail_url,
        duration=duration, file_size=file_size_bytes,
        uploaded_by_id=user_id
    )
    logger.info(f"Content saved with ID: {content.content_id} for user_id: {user_id}")
    return ContentResponse.model_validate(content)

async def _serialize_response(movies, total_used_mb, total_mb, current_plan):
    return UserLibraryResponse(
        total_storage=total_mb, used_storage=total_used_mb, current_plan=current_plan,
        your_movies=[ContentResponse(
            content_id=movie.content_id, title=movie.title, description=movie.description, url=movie.url, r2_key=movie.r2_key,
            thumbnail_url=movie.thumbnail_url, file_size=movie.file_size, duration=movie.duration, content_type=movie.content_type,
            created_at=movie.created_at
        ) for movie in movies]
    )

async def library(user_id: uuid.UUID, db: AsyncSession):
    stmt = select(Content).where(Content.uploaded_by_id == user_id)
    result = await db.execute(stmt)
    movie = result.scalars()
    total_used_mb = 0
    movies = list()

    if movie:
        movies = movie.all()
        for data in movies:
            movie_bytes = data.file_size
            file_mb = round(movie_bytes / (1024 * 1024), 2)
            total_used_mb += file_mb

    total_mb, current_plan = await user_service(db).check_active_user_subscription(user_id)
    
    return await _serialize_response(movies, total_used_mb, total_mb, current_plan)

