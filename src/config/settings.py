from pydantic_settings import BaseSettings, SettingsConfigDict

from dotenv import load_dotenv
load_dotenv()

class Setting(BaseSettings):

    DATABASE_URL: str
    OTP_Expiry: int
    BREVO_API_KEY: str
    BREVO_BASE_URL: str
    FROMEMAIL: str 
    FROMNAME: str
    APP_NAME: str = "Remote Cinema"
    TRIAL_PERIOD_DAYS: int = 5
    BASE_URL: str = "http://127.0.0.1:8000"
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str       
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15   
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7 

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'
    )

setting = Setting()
