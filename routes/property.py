# property.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query
from database import db
import cloudinary.uploader
from cloudinary_config import *   # ✅ ensures Cloudinary is configured
from routes.auth import get_current_user
from bson import ObjectId  # ✅ needed to convert MongoDB ObjectId

router = APIRouter()

VALID_CATEGORIES = ["house", "villa", "apartment", "farmlands", "plots", "buildings"]

# ---------------- Add property ----------------
@router.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    try:
        # Validate category
        if category.lower() not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of {VALID_CATEGORIES}"
            )

        # Upload image to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="real-estate-app",
                resource_type="auto"
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

        image_url = upload_result.get("secure_url")

        # Save property in DB
        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "category": category.lower(),
            "image_url": image_url,
            "owner": current_user["email"],
        }

        result = db.properties.insert_one(property_data)
        property_data["_id"] = str(result.inserted_id)

        return {"message": "Property added successfully", "property": property_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- My properties (logged-in user) ----------------
@router.get("/my-properties")
async def get_my_properties(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    properties = list(db.properties.find({"owner": user_email}))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties

# ---------------- Properties by category ----------------
@router.get("/category/{category}")
async def get_properties_by_category(category: str, search: str = None):
    if category.lower() not in VALID_CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category. Must be one of {VALID_CATEGORIES}"
        )

    query = {"category": category.lower()}

    # Optional search filter
    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    properties = list(db.properties.find(query))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties 