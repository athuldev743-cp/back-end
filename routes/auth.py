from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dummy user database (replace with MongoDB or your real DB)
fake_users_db = {
    "test@test.com": {
        "username": "testuser",
        "email": "test@test.com",
        "hashed_password": pwd_context.hash("123456")
    }
}

# JWT config
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET environment variable is missing")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

# Authenticate user
def authenticate_user(email: str, password: str):
    user = fake_users_db.get(email)
    if not user or not pwd_context.verify(password, user["hashed_password"]):
        return None
    return user

# Create JWT token
def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Decode JWT token
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return fake_users_db.get(email)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Login route
@router.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": user["email"]})
    return {"access_token": token, "token_type": "bearer"}

# Protected route
@router.get("/me")
def get_current_user(token: str = Depends(oauth2_scheme)):
    user = decode_access_token(token)
    return {"user": user}
