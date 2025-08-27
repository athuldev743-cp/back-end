from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property, chat, user  # 👈 removed email

app = FastAPI()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://estateuro.onrender.com"],  # your frontend domain
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
app.include_router(chat.router, tags=["chat"])
app.include_router(user.router, prefix="/user", tags=["user"])  # 👈 keep user
