from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from database import db
from fastapi.responses import JSONResponse
import cloudinary
import cloudinary.uploader

router = APIRouter()

# Configure Cloudinary
cloudinary.config(
    cloud_name = "<your_cloud_name>",  # or use env variables
    api_key = "<your_api_key>",
    api_secret = "<your_api_secret>",
    secure = True
)

# Add property route
@router.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    category: str = Form(...),
    location: str = Form(...),
    image: UploadFile = File(...)
):
    try:
        # Validate image type
        if image.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Invalid image type")

        # Upload image to Cloudinary
        result = cloudinary.uploader.upload(image.file, folder="estateuro_properties")
        image_url = result.get("secure_url")

        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "location": location,
            "image": image_url
        }

        db.properties.insert_one(property_data)
        return {"message": "Property added successfully!", "property": property_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get properties route
@router.get("/properties")
def get_properties(category: str = "", search: str = ""):
    try:
        query = {}
        if category:
            query["category"] = category
        if search:
            query["title"] = {"$regex": search, "$options": "i"}

        properties = list(db.properties.find(query, {"_id": 0}))
        return properties

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

