# main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, property, chat, user, chat_notifications
from routes.location import router as location_router
from routes.cart import cart_router
import logging
from fastapi.responses import JSONResponse

app = FastAPI(title="Estateuro API", version="1.0.0")

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- CORS --------------------
origins = [
    "https://real-estate-front-two.vercel.app",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# -------------------- Debug middleware --------------------
@app.middleware("http")
async def log_request(request: Request, call_next):
    origin = request.headers.get("origin")
    logger.info(f"🌍 Incoming request from Origin: {origin} {request.method} {request.url}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.exception(f"❌ Error processing request: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error. Check backend logs."}
        )

# -------------------- Root --------------------
@app.get("/")
def root():
    return {"message": "Backend running successfully 🚀"}

# -------------------- Routers --------------------
app.include_router(auth.router, prefix="/auth", tags=["auth"])

# === Removed /api prefix here ===
app.include_router(property.router, prefix="", tags=["property"])

app.include_router(user.router, prefix="/user", tags=["user"])
app.include_router(location_router, prefix="", tags=["location"])
app.include_router(cart_router, prefix="", tags=["cart"])
