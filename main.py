from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.auth import router as auth_router, get_current_user
from routes.property import router as property_router
from database import db

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://estateuro.onrender.com"],  # Your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Health check
@app.get("/health")
def health_check():
    try:
        db.list_collection_names()
        return JSONResponse(
            content={"status": "ok", "message": "Backend and database running!"},
            status_code=200
        )
    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": "Database connection failed", "details": str(e)},
            status_code=500
        )

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(property_router, prefix="/api", tags=["property"])

# Example protected route
@app.get("/api/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, this is a protected route!"}
