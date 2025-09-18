from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from routes import auth, property as property_routes, cart, location

app = FastAPI(title="Real Estate Backend", version="1.0.0")

# ---------------- CORS ----------------
origins = [
    "http://localhost:3000",  # local dev
    "https://real-estate-front-two.vercel.app",  # deployed frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,        # allow only these origins
    allow_credentials=True,       # cookies/auth headers allowed
    allow_methods=["*"],          # GET, POST, PUT, DELETE
    allow_headers=["*"],          # all headers like Authorization
)

# ---------------- Routers ----------------
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(property_routes.router, prefix="/api", tags=["property"])
app.include_router(cart.cart_router, prefix="/api", tags=["cart"])
app.include_router(location.router, prefix="/api", tags=["location"])

# ---------------- Root ----------------
@app.get("/")
def root():
    return {"message": "Backend running successfully ✅"}
