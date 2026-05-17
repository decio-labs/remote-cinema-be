import secrets
import hashlib
import bcrypt

from src.models.users.auth import OneTimePassword
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class OTPService:

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_otp(length=5):
        """Generates a random OTP of specified length."""
        return str(secrets.randbelow(10**length)).zfill(length)

    @staticmethod
    def hash_otp(otp):
        """Hashes the OTP using Bcrypt."""
        return bcrypt.hashpw(otp.encode('utf-8'), bcrypt.gensalt())

    async def verify_otp(self, provided_otp):
        """Verifies the provided OTP against the stored hashed OTP."""

        stmt = select(OneTimePassword).where(OneTimePassword.raw_code == provided_otp)
        result = await self.db.execute(stmt)
        otp_entry = result.scalar_one_or_none()

        is_valid = False
        message = ""
        user_id = None

        if not otp_entry:
            message = "no otp entry found"
            return is_valid, message, user_id

        if otp_entry.is_expired():
            message = "otp_instance expired"
            return is_valid, message, user_id

        if otp_entry.is_used:
            message = "otp instnace is used"
            return is_valid, message, user_id

        if not otp_entry.is_active:
            message = "otp is no longer active"
            return is_valid, message, user_id

        if bcrypt.checkpw(provided_otp.encode('utf-8'), otp_entry.hash_code):
            is_valid = True
            message = "otp is valid"
            user_id = otp_entry.user_id
            otp_entry.is_used = True
            otp_entry.is_active = False
            await self.db.commit()
            await self.db.refresh(otp_entry)
        else:
            message = "invalid otp"

        return is_valid, message, user_id

    async def create_and_store_otp(self, user_id):
        """Creates an OTP, hashes it, and stores it in the database."""
        otp = self.generate_otp()
        hashed_otp = self.hash_otp(otp)
        otp_entry = OneTimePassword(user_id=user_id, hash_code=hashed_otp, raw_code=otp)
        self.db.add(otp_entry)
        await self.db.commit()
        await self.db.refresh(otp_entry)
        return otp