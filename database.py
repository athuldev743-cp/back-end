import os
from pymongo import MongoClient

# Use environment variable for MongoDB URL (set in Render)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = MongoClient(MONGO_URL)
db = client["realestate"]  # Keep database name as 'realestate'
