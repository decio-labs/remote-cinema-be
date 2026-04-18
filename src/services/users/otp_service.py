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
        if not otp_entry:
            return False, None
        if otp_entry.is_expired():
            return False, None
        if otp_entry.is_used:
            return False, None
        if not otp_entry.is_active:
            return False, None
        is_valid = bcrypt.checkpw(provided_otp.encode('utf-8'), otp_entry.hash_code)

        if is_valid:
            # Mark the OTP as used and inactive after successful verification
            otp_entry.is_used = True
            otp_entry.is_active = False
            await self.db.commit()
            await self.db.refresh(otp_entry)

        return is_valid, otp_entry.user_id if is_valid else None

    async def create_and_store_otp(self, user_id):
        """Creates an OTP, hashes it, and stores it in the database."""
        otp = self.generate_otp()
        hashed_otp = self.hash_otp(otp)
        otp_entry = OneTimePassword(user_id=user_id, hash_code=hashed_otp, raw_code=otp)
        self.db.add(otp_entry)
        await self.db.commit()
        await self.db.refresh(otp_entry)
        return otp