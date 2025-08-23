# routes/property.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from database import db
import cloudinary.uploader
import cloudinary  # make sure config loads
import cloudinary_config  # 👈 this applies your .env settings
from routes.auth import get_current_user  # for protected routes

router = APIRouter()

# ---------- Add Property ----------
@router.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    location: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),  # only logged-in users can add
):
    try:
        # Upload image to Cloudinary
        upload_result = cloudinary.uploader.upload(
            image.file,
            folder="real-estate-app"
        )
        image_url = upload_result.get("secure_url")

        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "location": location,
            "image_url": image_url,
            "owner": current_user["email"],
        }

        db.properties.insert_one(property_data)
        return {"message": "Property added successfully", "property": property_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Get All Properties (public) ----------
@router.get("/properties")
async def get_properties():
    properties = list(db.properties.find({}, {"_id": 0}))  # exclude MongoDB _id
    return {"properties": properties}


# ---------- Get My Properties (protected) ----------
@router.get("/my-properties")
async def get_my_properties(current_user: dict = Depends(get_current_user)):
    properties = list(db.properties.find({"owner": current_user["email"]}, {"_id": 0}))
    return {"properties": properties}
