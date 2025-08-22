from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from routes.auth import router as auth_router, get_current_user
from routes.property import router as property_router
from database import db  # your MongoDB connection

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this to your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Health check route for Uptime Robot
@app.get("/health")
def health_check():
    """
    Endpoint to check backend and database health.
    Returns 200 OK if backend is running and MongoDB is connected.
    Returns 500 if database connection fails.
    """
    try:
        # Check MongoDB connection by listing collections
        db.list_collection_names()
        return JSONResponse(
            content={"status": "ok", "message": "Backend and database are running!"},
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
