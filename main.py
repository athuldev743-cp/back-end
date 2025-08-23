# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property  # make sure both files exist inside routes/

app = FastAPI()

# CORS setup (allow frontend to talk to backend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# Routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(property.router, prefix="/api", tags=["property"])
