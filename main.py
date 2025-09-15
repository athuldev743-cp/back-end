from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property, chat, user, chat_notifications
from routes.location import router as location_router

app = FastAPI()

# -------------------- CORS --------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://real-estate-front-two.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Debug middleware to check incoming origin
@app.middleware("http")
async def log_request(request: Request, call_next):
    origin = request.headers.get("origin")
    print("🌍 Incoming request from Origin:", origin)
    response = await call_next(request)
    return response

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
app.include_router(location_router, prefix="/api")
