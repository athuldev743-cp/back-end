from fastapi import APIRouter, UploadFile, File, Form
from database import db
import shutil, os

router = APIRouter()
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


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
        file_location = f"{UPLOAD_FOLDER}/{image.filename}"
        with open(file_location, "wb") as f:
            shutil.copyfileobj(image.file, f)

        property_data = {
            "title": title,
            "description": description,
            "price": price,
            "category": category,
            "location": location,
            "image": f"/uploads/{image.filename}"
        }
        db.properties.insert_one(property_data)
        return {"message": "Property added successfully!", "property": property_data}
    except Exception as e:
        return {"error": str(e)}


@router.get("/properties")
def get_properties(category: str = "", search: str = ""):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    return list(db.properties.find(query, {"_id": 0}))
