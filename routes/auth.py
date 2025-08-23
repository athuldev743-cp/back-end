from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from dotenv import load_dotenv
from database import db  # Your MongoDB connection
import os

# Load environment variables
load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET environment variable is missing")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# FastAPI router
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


# ---------- Password helpers ----------
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# ---------- JWT helpers ----------
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Exclude hashed password from response
    user.pop("password", None)
    return user


# ---------- Register endpoint ----------
@router.post("/register")
def register(username: str = Form(...), password: str = Form(...)):
    if db.users.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = hash_password(password)
    db.users.insert_one({"username": username, "password": hashed})
    return {"message": "User registered successfully"}


# ---------- Login endpoint ----------
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(
        data={"sub": form_data.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ---------- Protected endpoint ----------
@router.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
