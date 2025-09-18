from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ✅ Import all routers
from routes import auth, property as property_routes, cart, location
# Chat endpoints are already inside property.py, so no separate import

app = FastAPI(title="Real Estate Backend", version="1.0.0")

# ---------------- CORS ----------------
origins = [
    "http://localhost:3000",  # local dev
    "https://real-estate-front-two.vercel.app",  # deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Routers ----------------
# Auth
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth.router, prefix="/auth", tags=["auth-legacy"])  # legacy fallback

# Property (includes chat endpoints)
app.include_router(property_routes.router, prefix="/api", tags=["property"])
app.include_router(property_routes.router, prefix="", tags=["property-legacy"])  # legacy fallback

# Cart
app.include_router(cart.cart_router, prefix="/api", tags=["cart"])
app.include_router(cart.cart_router, prefix="", tags=["cart-legacy"])  # legacy fallback

# Location search
app.include_router(location.router, prefix="/api", tags=["location"])
app.include_router(location.router, prefix="", tags=["location-legacy"])  # legacy fallback

# ---------------- Root ----------------
@app.get("/")
def root():
    return {"message": "Backend running successfully ✅"}
