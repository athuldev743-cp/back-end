# routes/auth.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from database import db
import os
import random
import smtplib
import secrets
from dotenv import load_dotenv
from routes.dependencies import get_current_user
import hashlib

load_dotenv()
router = APIRouter()

# ---------------- Security / Config ----------------
JWT_SECRET = os.getenv("JWT_SECRET", "supersecret")
REFRESH_SECRET = os.getenv("REFRESH_SECRET", "refreshsupersecret")
ALGORITHM = "HS256"

# expiration minutes
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 7))  # default 7 days
REFRESH_TOKEN_EXPIRE_MINUTES = int(os.getenv("REFRESH_TOKEN_EXPIRE_MINUTES", 60 * 24 * 30))  # default 30 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------- Models ----------------
class UserRegister(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str | None = None

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ---------------- Helpers ----------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(data: dict, secret: str, expires_minutes: int, token_type: str = "access"):
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    payload.update({"exp": expire, "type": token_type})
    return jwt.encode(payload, secret, algorithm=ALGORITHM)

def create_access_token_for_user(email: str):
    return create_jwt_token({"email": email}, JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES, token_type="access")

def create_refresh_token_for_user(email: str):
    return create_jwt_token({"email": email}, REFRESH_SECRET, REFRESH_TOKEN_EXPIRE_MINUTES, token_type="refresh")

def send_otp_email(to_email: str, otp: str) -> bool:
    sender = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    subject = "Your OTP for Estateuro Registration"
    body = f"Your OTP is: {otp}\nThis OTP will expire in 5 minutes."
    message = f"Subject: {subject}\n\n{body}"
    try:
        with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT", 587))) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, to_email, message)
        print(f"✅ OTP sent to {to_email}")
        return True
    except Exception as e:
        print("❌ Error sending email:", e)
        return False

def format_user_response(user: dict, access_token: str | None = None, refresh_token: str | None = None):
    # safe fields returned to client
    resp = {
        "fullName": user.get("fullName"),
        "email": user.get("email"),
        "phone": user.get("phone"),
        "is_verified": user.get("is_verified", False),
    }
    if access_token:
        resp.update({"access_token": access_token, "token_type": "bearer"})
    if refresh_token:
        resp.update({"refresh_token": refresh_token})
    return resp

# ---------------- Routes ----------------
@router.post("/register")
async def register(request: UserRegister):
    existing = await db.users.find_one({"email": request.email})

    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.utcnow() + timedelta(minutes=5)
    hashed_pw = hash_password(request.password)

    if existing:
        if existing.get("is_verified"):
            raise HTTPException(status_code=400, detail="Email already registered")
        await db.users.update_one(
            {"email": request.email},
            {"$set": {
                "otp": otp,
                "otp_expires": expiry_time,
                "password": hashed_pw,
                "fullName": request.fullName,
                "phone": request.phone
            }}
        )
        if not send_otp_email(request.email, otp):
            raise HTTPException(status_code=500, detail="Failed to send OTP email")
        return {"message": "Email already registered but not verified. New OTP sent."}

    await db.users.insert_one({
        "fullName": request.fullName,
        "email": request.email,
        "password": hashed_pw,
        "phone": request.phone,
        "otp": otp,
        "otp_expires": expiry_time,
        "is_verified": False,
        "activities": [],
        "refresh_token": None
    })

    if not send_otp_email(request.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"message": "OTP sent to your email. Verify to complete registration."}

@router.post("/resend-otp")
async def resend_otp(request: ResendOTPRequest):
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.utcnow() + timedelta(minutes=5)

    await db.users.update_one(
        {"email": request.email},
        {"$set": {"otp": otp, "otp_expires": expiry_time}}
    )

    if not send_otp_email(request.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"message": "New OTP sent to your email."}

@router.post("/verify-otp")
async def verify_otp(request: UserVerifyOTP):
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("otp") != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if datetime.utcnow() > user.get("otp_expires", datetime.utcnow()):
        raise HTTPException(status_code=400, detail="OTP expired")

    await db.users.update_one(
        {"email": request.email},
        {"$set": {"is_verified": True}, "$unset": {"otp": "", "otp_expires": ""}}
    )

    user = await db.users.find_one({"email": request.email})

    access_token = create_access_token_for_user(request.email)
    refresh_token = create_refresh_token_for_user(request.email)

    await db.users.update_one({"email": request.email}, {"$set": {"refresh_token": refresh_token}})

    return format_user_response(user, access_token=access_token, refresh_token=refresh_token)

@router.post("/login")
async def login(request: UserLogin):
    user = await db.users.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = create_access_token_for_user(request.email)
    refresh_token = create_refresh_token_for_user(request.email)

    await db.users.update_one({"email": request.email}, {"$set": {"refresh_token": refresh_token}})

    return format_user_response(user, access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh-token")
async def refresh_token(req: RefreshTokenRequest):
    token = req.refresh_token
    if not token:
        raise HTTPException(status_code=400, detail="Refresh token required")

    try:
        payload = jwt.decode(token, REFRESH_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh" or "email" not in payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    email = payload.get("email")
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stored = user.get("refresh_token")
    if not stored or stored != token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or invalid")

    new_access = create_access_token_for_user(email)
    new_refresh = create_refresh_token_for_user(email)

    await db.users.update_one({"email": email}, {"$set": {"refresh_token": new_refresh}})

    user = await db.users.find_one({"email": email})
    return format_user_response(user, access_token=new_access, refresh_token=new_refresh)

@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    await db.users.update_one({"email": email}, {"$set": {"refresh_token": None}})
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    return format_user_response(current_user)
