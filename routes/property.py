# routes/property.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Query
from database import db
from routes.auth import get_current_user
from cloudinary_config import cloudinary
from pymongo.errors import DuplicateKeyError
from bson import ObjectId

router = APIRouter()

@router.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if price <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image type")

    try:
        result = cloudinary.uploader.upload(image.file, folder="estateuro_properties")
        image_url = result.get("secure_url")
        if not image_url:
            raise HTTPException(status_code=500, detail="Failed to upload image")

        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "location": location,
            "image": image_url,
            "created_by": current_user["email"]
        }

        inserted = db.properties.insert_one(property_data)
        property_data["_id"] = str(inserted.inserted_id)  # return ID as string
        return {"message": "Property added successfully!", "property": property_data}

    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="Property with this title already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties")
def get_properties(
    category: str = "",
    search: str = "",
    skip: int = 0,
    limit: int = Query(10, le=50)
):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    try:
        properties = list(db.properties.find(query).skip(skip).limit(limit))
        # Convert ObjectId to string
        for prop in properties:
            prop["_id"] = str(prop["_id"])
        return properties
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{property_id}")
def get_property_detail(property_id: str):
    """Get single property by ID"""
    try:
        property_item = db.properties.find_one({"_id": ObjectId(property_id)})
        if not property_item:
            raise HTTPException(status_code=404, detail="Property not found")
        property_item["_id"] = str(property_item["_id"])
        return property_item
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid property ID")
