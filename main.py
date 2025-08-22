# main.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
import shutil, os

app = FastAPI()

# ---------------- CORS ----------------
origins = ["http://localhost:3000"]  # your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- MongoDB ----------------
client = MongoClient("mongodb://localhost:27017")
db = client["realestate"]
collection = db["properties"]

# ---------------- Uploads Folder ----------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Serve uploads as static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")

# ---------------- Routes ----------------

@app.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # Save the image
        file_location = f"{UPLOAD_FOLDER}/{image.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(image.file, f)

        # Prepare property data
        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "location": location,
            "image": f"/uploads/{image.filename}"  # relative path for frontend
        }

        # Insert into MongoDB
        collection.insert_one(property_data)

        return {"message": "Property added successfully!", "property": property_data}

    except Exception as e:
        return {"error": str(e)}


@app.get("/properties/")
async def get_properties(category: str, search: str = ""):
    query = {"category": category}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}  # case-insensitive search

    properties = list(collection.find(query, {"_id": 0}))
    return properties
