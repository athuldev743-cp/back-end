from fastapi import APIRouter, HTTPException, UploadFile, Form, Depends
from routes.auth import get_current_user
from database import db
import cloudinary.uploader
from cloudinary_config import *
from datetime import datetime

router = APIRouter()

VALID_CATEGORIES = ["house", "villa", "apartment", "farmlands", "plots", "buildings"]

@router.post("/upload-property")
async def upload_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    category: str = Form(...),
    mobileNO: str = Form(...),
    image: UploadFile = None,
    current_user: dict = Depends(get_current_user),
):
    try:
        if category.lower() not in VALID_CATEGORIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid category. Must be one of {VALID_CATEGORIES}"
            )

        # Upload image if provided
        image_url = None
        if image:
            try:
                upload_result = cloudinary.uploader.upload(
                    image.file,
                    folder="real-estate-app",
                    resource_type="auto"
                )
                image_url = upload_result.get("secure_url")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "category": category.lower(),
            "image_url": image_url,
            "owner": current_user["email"],
            "ownerFullName": current_user.get("fullName", ""),
            "mobileNO": mobileNO,
            "created_at": datetime.utcnow()
        }

        result = db.properties.insert_one(property_data)
        property_data["_id"] = str(result.inserted_id)

        return {"message": "Property added successfully", "property": property_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
