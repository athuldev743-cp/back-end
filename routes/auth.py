# routes/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from database import db
import os, random, smtplib
from dotenv import load_dotenv
from routes.dependencies import get_current_user  
from fastapi import Depends

load_dotenv()
router = APIRouter()

# ---------------- Security ----------------
SECRET_KEY = os.getenv("JWT_SECRET", "supersecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------- Models ----------------
class UserRegister(BaseModel):
    fullName: str
    email: EmailStr
    password: str

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

# ---------------- Utils ----------------
def create_access_token(data: dict, expires_delta: int = ACCESS_TOKEN_EXPIRE_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str):
    return pwd_context.hash(password)

def send_otp_email(to_email: str, otp: str):
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

# ---------------- Routes ----------------
@router.post("/register")
def register(request: UserRegister):
    existing = db.users.find_one({"email": request.email})

    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.utcnow() + timedelta(minutes=5)
    hashed_pw = hash_password(request.password)

    if existing:
        if existing.get("is_verified"):
            raise HTTPException(status_code=400, detail="Email already registered")
        db.users.update_one(
            {"email": request.email},
            {"$set": {
                "otp": otp,
                "otp_expires": expiry_time,
                "password": hashed_pw,
                "fullName": request.fullName
            }}
        )
        if not send_otp_email(request.email, otp):
            raise HTTPException(status_code=500, detail="Failed to send OTP email")
        return {"message": "Email already registered but not verified. New OTP sent."}

    db.users.insert_one({
        "fullName": request.fullName,
        "email": request.email,
        "password": hashed_pw,
        "otp": otp,
        "otp_expires": expiry_time,
        "is_verified": False,
        "activities": []
    })

    if not send_otp_email(request.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"message": "OTP sent to your email. Verify to complete registration."}

@router.post("/resend-otp")
def resend_otp(request: ResendOTPRequest):
    user = db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Email already verified")

    otp = str(random.randint(100000, 999999))
    expiry_time = datetime.utcnow() + timedelta(minutes=5)

    db.users.update_one(
        {"email": request.email},
        {"$set": {"otp": otp, "otp_expires": expiry_time}}
    )

    if not send_otp_email(request.email, otp):
        raise HTTPException(status_code=500, detail="Failed to send OTP email")

    return {"message": "New OTP sent to your email."}

@router.post("/verify-otp")
def verify_otp(request: UserVerifyOTP):
    user = db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.get("otp") != request.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    if datetime.utcnow() > user.get("otp_expires", datetime.utcnow()):
        raise HTTPException(status_code=400, detail="OTP expired")

    db.users.update_one(
        {"email": request.email},
        {"$set": {"is_verified": True}, "$unset": {"otp": "", "otp_expires": ""}}
    )

    token = create_access_token({"email": request.email})
    return {"access_token": token, "token_type": "bearer", "fullName": user["fullName"]}

@router.post("/login")
def login(request: UserLogin):
    user = db.users.find_one({"email": request.email})
    if not user or not verify_password(request.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_verified", False):
        raise HTTPException(status_code=403, detail="Email not verified")

    token = create_access_token({"email": request.email})
    return {"access_token": token, "token_type": "bearer", "fullName": user["fullName"]}

# ---------- FIXED /me ROUTE ----------
@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    try:
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        # Only return safe fields
        return {
            "fullName": current_user.get("fullName"),
            "email": current_user.get("email"),
            "is_verified": current_user.get("is_verified", False),
        }
    except Exception as e:
        # Log error for debugging
        print("Error in /me route:", e)
        raise HTTPException(status_code=500, detail="Internal server error")
