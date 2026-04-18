import uuid

from pydantic import BaseModel, field_validator, constr, model_validator
from pydantic import BaseModel, EmailStr

from typing import Annotated
from datetime import datetime
import logging
import email_validator

logger = logging.getLogger(__name__)

class RegSchema(BaseModel):

    email: Annotated[EmailStr, constr(strip_whitespace=True, max_length=255)]
    password: Annotated[str, constr(max_length=255, min_length=8)]

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, value):
        try:
            valid_email = email_validator.validate_email(value, check_deliverability=True)
        except email_validator.EmailNotValidError as exc:
            logger.error("email not valid", str(exc))
            raise ValueError(exc)
        return valid_email.normalized


class RegResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True 

class VerifySchema(BaseModel):
    otp_code: Annotated[str, constr(strip_whitespace=True, max_length=10, min_length=5)]


class ResendOTPSchema(BaseModel):
    email: Annotated[str, constr(strip_whitespace=True, max_length=255)]


class PasswordResetSchema(BaseModel):
    password: Annotated[str, constr(max_length=255, min_length=8)]
    confirm_password: Annotated[str, constr(max_length=255, min_length=8)]

    @model_validator(mode="after")
    def passwords_match(cls, values):
        password, confirm_password = values.password, values.confirm_password
        if password != confirm_password:
            raise ValueError("Passwords do not match")
        return values

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value
    

class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class AccessTokenPayload(BaseModel):
    sub: str          # user_id
    email: str
    role: str
    jti: str       
    exp: int
    iat: int


class RefreshTokenPayload(BaseModel):
    sub: str     # user_id
    jti: str        
    exp: int
    iat: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str

