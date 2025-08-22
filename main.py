from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from routes.auth import router as auth_router, get_current_user
from routes.property import router as property_router
from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(property_router, prefix="/api", tags=["property"])

# Example protected route
@app.get("/api/protected")
def protected_route(current_user: dict = Depends(get_current_user)):
    return {"message": f"Hello {current_user['username']}, this is a protected route!"}
