from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

# Import only existing routes
from routes import auth, property, user
from routes.location import router as location_router
from routes.cart import cart_router

app = FastAPI(title="Estateuro API", version="1.0.0")

# -------------------- Logging --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------------- CORS --------------------
origins = [
    "https://real-estate-front-two.vercel.app",  # your deployed frontend
    "http://localhost:3000",                     # local React dev
    "http://127.0.0.1:3000",                     # alternative local
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# -------------------- Debug Middleware --------------------
@app.middleware("http")
async def log_request(request: Request, call_next):
    origin = request.headers.get("origin")
    logger.info(f"🌍 Request from Origin: {origin} {request.method} {request.url}")
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
# NOTE: these match frontend usage
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(property.router, prefix="/api", tags=["property"])  # ✅ contains /category/{category}
app.include_router(user.router, prefix="/api/user", tags=["user"])
app.include_router(location_router, prefix="/api", tags=["location"])
app.include_router(cart_router, prefix="/api/cart", tags=["cart"])
