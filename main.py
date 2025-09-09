from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property, chat, user, chat_notifications

app = FastAPI()

# -------------------- CORS --------------------
origins = [
    "https://real-estate-front-6o4p5btyx-athul-devs-projects.vercel.app",  # your production frontend
    "http://localhost:3000",           # local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------- Root --------------------
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# -------------------- Routers --------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(property.router, prefix="/api", tags=["property"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(chat_notifications.router, prefix="/chat", tags=["chat_notifications"])
