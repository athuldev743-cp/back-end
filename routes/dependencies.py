# routes/dependencies.py
from fastapi import Header, HTTPException
from jose import jwt
from database import db
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"

def get_current_user(authorization: str = Header(...)):
    """
    Extract Bearer token from Authorization header and return current user.
    Example header: "Authorization: Bearer <token>"
    """
    try:
        token = authorization.split(" ")[1]  # get the token part
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = db.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
