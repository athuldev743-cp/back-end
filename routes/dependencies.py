# dependencies.py
from fastapi import Header
from jose import jwt, JWTError
from database import db
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"

async def get_current_user(authorization: str | None = Header(None)):
    """
    Returns the user dict if the token is valid, otherwise returns None.
    This prevents raising HTTPException inside the dependency, which fixes CORS issues.
    Routes should check for None and handle authentication explicitly.
    """
    if not authorization:
        return None  # missing token

    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            return None  # invalid auth scheme
    except ValueError:
        return None  # invalid header format

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        if not email:
            return None  # invalid token payload
        user = await db.users.find_one({"email": email})
        return user  # may be None if user not found
    except JWTError:
        return None  # expired or invalid token
