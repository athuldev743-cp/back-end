# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import your routers
from routes import auth  # auth.py
from routes import properties  # properties.py
from routes import chat  # chat.py
# Add other routers here if needed

app = FastAPI(
    title="Estateuro API",
    description="Backend API for Estateuro Real Estate Platform",
    version="1.0.0"
)

# ----- CORS Configuration -----
frontend_local = "http://localhost:3000"
frontend_prod = os.getenv("FRONTEND_URL", "https://real-estate-front-two.vercel.app")

origins = [frontend_local, frontend_prod]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # frontend domains allowed
    allow_credentials=True,  # allow cookies / auth headers
    allow_methods=["*"],     # GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],     # allow custom headers
)

# ----- Include Routers -----
app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(properties.router, prefix="/api", tags=["Properties"])
app.include_router(chat.router, prefix="/chat", tags=["Chat"])
# Add any additional routers similarly

# ----- Root Endpoint -----
@app.get("/")
def root():
    return {"message": "Estateuro Backend is running ✅"}

# ----- Optional Health Check -----
@app.get("/health")
def health():
    return {"status": "ok", "time": str(os.getenv("TIMEZONE", "UTC"))}
