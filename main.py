from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property  # your routers

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://estateuro.onrender.com"],  # frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(property.router, prefix="/api", tags=["property"])
