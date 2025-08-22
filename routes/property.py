from fastapi import APIRouter, Depends, Query
from models import Property
from database import db
from bson import ObjectId
from routes.auth import get_current_user

router = APIRouter()

# Add property
@router.post("/add-property")
def add_property(property: Property, user: dict = Depends(get_current_user)):
    property_dict = property.dict()
    property_dict["owner"] = user["username"]
    result = db.properties.insert_one(property_dict)
    return {"id": str(result.inserted_id), "message": "Property added successfully!"}

# Get properties (with optional category or search)
@router.get("/properties")
def get_properties(category: str = None, search: str = None):
    query = {}
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"category": {"$regex": search, "$options": "i"}}
        ]
    properties = list(db.properties.find(query))
    for p in properties:
        p["_id"] = str(p["_id"])
    return properties
