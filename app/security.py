import os
import jwt
from datetime import datetime, timedelta, timezone
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()
JWT_SECRET = os.getenv("JWT_SECRET", "development-secret-change-this")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = 60 * 12

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)

def create_token(username: str) -> str:
    payload = {
        "sub": username,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.PyJWTError:
        return None
