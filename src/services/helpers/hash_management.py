import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class HashService:
    def hash_password(password: str):
        return pwd_context.hash(password)
    
    def verify_password(password: str, hashed_password):
        return pwd_context.verify(password, hashed_password)
    
    def hash_token(token: str):
        return pwd_context.hash(token)
    
    def verify_token(token: str, hashed_token: bytes):
        return pwd_context.verify(token, hashed_token)
