import hashlib
import os
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.config import BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD

security = HTTPBasic()

def hash_password(password: str) -> str:
    # Hash a password using PBKDF2 with SHA-256
    salt = os.urandom(16)
    db_val = salt + hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return db_val.hex()

# Verify a password
def verify_password(password: str, hashed: str) -> bool:
    try:
        db_val = bytes.fromhex(hashed)
        salt = db_val[:16]
        key = db_val[16:]
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return secrets.compare_digest(new_key, key)
    except Exception:
        return False

def get_current_user(
    credentials: HTTPBasicCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    # 1. Fallback check for standard credentials
    is_default_admin = (
        secrets.compare_digest(credentials.username, BASIC_AUTH_USERNAME) and
        secrets.compare_digest(credentials.password, BASIC_AUTH_PASSWORD)
    )
    if is_default_admin:
        return credentials.username

    # 2. Check the registered database users
    user = db.query(User).filter(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return user.username

