from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
import logging
from typing import Self

from functools import lru_cache

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("uvicorn.error")


VIDEO_MIME_TYPES = {
    '.mp4': 'video/mp4',
    '.mkv': 'video/x-matroska',
    '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime',
    '.wmv': 'video/x-ms-wmv',
    '.flv': 'video/x-flv',
    '.webm': 'video/webm',
    '.m4v': 'video/mp4',
    '.3gp': 'video/3gpp',
    '.ogv': 'video/ogg',
    '.ts': 'video/mp2t',
    '.mts': 'video/mp2t',
    '.vob': 'video/dvd',
    '.vtt': 'text/vtt'
}

class Settings(BaseSettings):

    DATABASE_URL: str
    OTP_Expiry: int
    BREVO_API_KEY: str
    BREVO_BASE_URL: str
    FROMEMAIL: str 
    FROMNAME: str
    APP_NAME: str = "Remote Cinema"
    TRIAL_PERIOD_DAYS: int = 5
    BASE_URL: str 
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str       
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15   
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7 
    STORAGE_ENDPOINT_URL: str
    CLOUDFLARE_R2_ACCESS_KEY_ID: str
    CLOUDFLARE_R2_SECRET_ACCESS_KEY: str
    CLOUDFLARE_R2_BUCKET_NAME: str
    CLOUDFLARE_R2_PUBLIC_URL: str
    VIDEO_MIME_TYPES: dict = VIDEO_MIME_TYPES
    CHUNK_SIZE: int = 50 * 1024 * 1024 # UPLOAD MEDIA IN CHUNKS 
    THUMBNAIL_GENERATION_SERVICE_URL: str
    REDIS_URL: str
    GOOGLE_CLOUD_ID: str
    GOOGLE_CLOUD_SECRET: str
    PAYSTACK_BASE_URL: str
    PAYSTACK_SECRET_KEY: str = "Paystack_secret_key"
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

    @model_validator(mode="after")
    def _warn_weak_tokens(self) -> Self:

        weak_tokens = ['secret_key', "jwt_secret_key", "change_me", "your_jwt_secret_key"]
        if self.JWT_REFRESH_SECRET_KEY.lower() in weak_tokens or self.JWT_SECRET_KEY in weak_tokens:
            logger.warning(
                 "JWT_SECRET appears weak or is a placeholder. "
            )

        if len(self.JWT_REFRESH_SECRET_KEY) < 32 or len(self.JWT_SECRET_KEY) < 32:
            logger.warning(
                "Use a cryptographically random string of ≥32 characters in production."
            )

        return self
@lru_cache
def  get_settings() -> Settings:
    settings = Settings()
    logger.info("Setting Loaded")
    return settings
