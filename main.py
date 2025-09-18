from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all routers
from routes import auth, property as property_routes, cart, location

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

# Property routes (includes chat endpoints)
app.include_router(property_routes.router, prefix="/api", tags=["property"])

# Cart routes
app.include_router(cart.cart_router, prefix="/api", tags=["cart"])

# Location search
app.include_router(location.router, prefix="/api", tags=["location"])

# ---------------- Root ----------------
@app.get("/")
def root():
    return {"message": "Backend running successfully ✅"}
