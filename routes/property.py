# property.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from database import db
import cloudinary.uploader
from cloudinary_config import *   # ✅ ensures Cloudinary is configured
from routes.auth import get_current_user

router = APIRouter()

VALID_CATEGORIES = ["house", "villa", "apartment", "farmlands", "plots", "buildings"]

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
        # ✅ Validate category
        if category.lower() not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of {VALID_CATEGORIES}"
            )

        # ✅ Upload image to Cloudinary
        try:
            upload_result = cloudinary.uploader.upload(
                image.file,
                folder="real-estate-app",
                resource_type="auto"   # 👈 handles jpg, png, pdf, etc.
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

        image_url = upload_result.get("secure_url")

        # ✅ Save property in DB
        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "category": category.lower(),   # 👈 store lowercase for consistency
            "image_url": image_url,
            "owner": current_user["email"],
        }

        db.properties.insert_one(property_data)
        return {"message": "Property added successfully", "property": property_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
