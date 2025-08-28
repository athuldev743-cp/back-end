from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    fullName: str          # NEW
    email: EmailStr
    password: str

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
