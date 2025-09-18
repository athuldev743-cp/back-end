from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ✅ Rename property import to avoid reserved word conflict
from routes import auth, property as property_routes, user, category

app = FastAPI()

# Allow frontend domain
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

# ✅ Auth routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(auth.router, prefix="/auth", tags=["auth-legacy"])  # for old frontend calls

# ✅ Property routes
app.include_router(property_routes.router, prefix="/api", tags=["property"])
app.include_router(property_routes.router, prefix="", tags=["property-legacy"])  # fallback

# ✅ User routes
app.include_router(user.router, prefix="/api/user", tags=["user"])

# ✅ Category routes
app.include_router(category.router, prefix="/api/category", tags=["category"])


@app.get("/")
def root():
    return {"message": "Backend running successfully ✅"}
