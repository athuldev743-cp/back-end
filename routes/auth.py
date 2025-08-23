from fastapi import APIRouter, HTTPException, Depends, Form
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Dummy user storage (replace with MongoDB logic)
fake_users_db = {
    "test@test.com": {
        "username": "testuser",
        "email": "test@test.com",
        "hashed_password": pwd_context.hash("123456")
    }
}

SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def authenticate_user(email: str, password: str):
    user = fake_users_db.get(email)
    if not user:
        return False
    if not pwd_context.verify(password, user["hashed_password"]):
        return False
    return user

def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Login route
@router.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access_token = create_access_token({"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}

# Optional: Protected user route
@router.get("/me")
def get_current_user(current_user: dict = Depends(lambda: fake_users_db["test@test.com"])):
    return {"user": current_user}
