from pydantic import BaseModel

class Property(BaseModel):
    title: str
    description: str
    price: float
    category: str   # plots, houses, apartments, etc.
    location: str

class User(BaseModel):
    username: str
    password: str
