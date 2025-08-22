from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import your auth router and function
from routes.auth import router as auth_router, get_current_user
from database import db  # ensures db initializes

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all for dev
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

# ---------------- Example Protected Route ----------------
@app.get("/api/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, this is a protected route!"}
