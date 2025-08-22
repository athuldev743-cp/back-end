from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from database import db  # just to ensure db initializes

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for dev, allow all. In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Routes ----------------
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Auth routes
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


# Example of a protected route
from auth import get_current_user
from fastapi import Depends

@app.get("/api/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, this is a protected route!"}
