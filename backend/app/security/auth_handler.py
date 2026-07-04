import hashlib
import os
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

# Secret config
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkeyreplaceinproduction")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class AuthHandler:
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using PBKDF2 HMAC SHA256 (built-in and robust).
        Returns salt and hash concatenated in hex format.
        """
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex() + ":" + pwd_hash.hex()

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password.
        """
        try:
            salt_hex, hash_hex = hashed_password.split(":")
            salt = bytes.fromhex(salt_hex)
            target_hash = bytes.fromhex(hash_hex)
            
            check_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
            return check_hash == target_hash
        except Exception:
            return False

    @staticmethod
    def create_access_token(user_id: str, email: str) -> str:
        """
        Create a JWT token.
        """
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> Optional[Dict]:
        """
        Decode and verify JWT token. Returns payload dict or None.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

auth_handler = AuthHandler()
