# from fastapi import FastAPI, Depends
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse
# from routes.auth import router as auth_router, get_current_user
# from routes.property import router as property_router
# from database import db  # your MongoDB connection

# app = FastAPI()

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:3000",  # dev frontend
#         "https://estateuro.onrender.com"  # deployed frontend
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Root route
# @app.get("/")
# def root():
#     return {"message": "Backend running successfully 🚀"}

# # Health check
# @app.get("/health")
# def health_check():
#     try:
#         db.list_collection_names()
#         return JSONResponse(
#             content={"status": "ok", "message": "Backend and database running!"},
#             status_code=200
#         )
#     except Exception as e:
#         return JSONResponse(
#             content={"status": "error", "message": "Database connection failed", "details": str(e)},
#             status_code=500
#         )

# # Include routers
# app.include_router(auth_router, prefix="/auth", tags=["auth"])  # Match frontend
# app.include_router(property_router, prefix="/api", tags=["property"])

# # Example protected route
# @app.get("/api/protected")
# def protected_route(current_user: dict = Depends(get_current_user)):
#     return {"message": f"Hello {current_user['username']}, this is a protected route!"}
# Temporary test route for MongoDB connectivity
from fastapi import FastAPI
from database import db  # db is your MongoDB database object
import os

app = FastAPI()

# =========================
# Test MongoDB Connection
# =========================
@app.get("/test-db")
def test_db():
    try:
        # Use db.client to access the MongoClient instance
        db.client.admin.command("ping")
        return {"status": "ok", "message": "MongoDB connection successful ✅"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
