# database.py
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL environment variable is missing")

client = MongoClient(MONGO_URL)
db = client["realestate"]

# Optional: Test connection
try:
    client.admin.command("ping")
    print("MongoDB connection successful ✅")
except Exception as e:
    raise RuntimeError(f"MongoDB connection failed: {e}")
