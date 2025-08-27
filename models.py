from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRegister(BaseModel):
    email: EmailStr
    password: str

class UserVerifyOTP(BaseModel):
    email: EmailStr
    otp: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Property(BaseModel):
    title: str
    description: str
    price: float
    category: str   # plots, houses, apartments, etc.
    location: str
