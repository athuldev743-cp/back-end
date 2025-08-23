import os
from pymongo import MongoClient

# Load MongoDB URL from environment variables
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL environment variable is missing")

# Connect to MongoDB
client = MongoClient(MONGO_URL)

# Database name
db = client["realestate"]

# Optional: Check connection at startup
try:
    client.admin.command("ping")
    print("MongoDB connection successful ✅")
except Exception as e:
    raise RuntimeError(f"MongoDB connection failed: {e}")
