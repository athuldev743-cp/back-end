# main.py
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router
from routes.property import router as property_router

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://estateuro.onrender.com"],  # replace with your frontend URL if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(property_router, prefix="/api", tags=["property"])
