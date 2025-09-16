# routes/property.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from database import db
import cloudinary.uploader
from cloudinary_config import *
from routes.dependencies import get_current_user  # ✅ updated
from bson import ObjectId
from datetime import datetime
from fastapi import status

router = APIRouter()

VALID_CATEGORIES = ["house", "villa", "apartment", "farmlands", "plots", "buildings"]
@router.post("/add-property")
async def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    latitude: float = Form(...),          # <-- new
    longitude: float = Form(...),         # <-- new
    category: str = Form(...),
    mobileNO: str = Form(...),
    images: list[UploadFile] = File(...), # <-- multiple images
    current_user: dict = Depends(get_current_user),
):
    if category.lower() not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {VALID_CATEGORIES}")

    image_urls = []
    try:
        for img in images:
            upload_result = cloudinary.uploader.upload(img.file, folder="real-estate-app", resource_type="auto")
            image_urls.append(upload_result.get("secure_url"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cloudinary upload failed: {str(e)}")

    property_data = {
        "title": title,
        "description": description,
        "price": price,
        "latitude": latitude,             # store coordinates
        "longitude": longitude,
        "category": category.lower(),
        "images": image_urls,             # store as list of URLs
        "owner": current_user["email"],
        "ownerFullName": current_user.get("fullName", ""),
        "mobileNO": mobileNO,
        "created_at": datetime.utcnow()
    }

    result = db.properties.insert_one(property_data)
    property_data["_id"] = str(result.inserted_id)
    return {"message": "Property added successfully", "property": property_data}


@router.get("/my-properties")
async def get_my_properties(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    properties = list(db.properties.find({"owner": user_email}))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties

@router.get("/category/{category}")
async def get_properties_by_category(category: str, search: str = None):
    if category.lower() not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {VALID_CATEGORIES}")
    query = {"category": category.lower()}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    properties = list(db.properties.find(query))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties

@router.get("/property/{property_id}")
async def get_property_by_id(property_id: str):
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop["_id"] = str(prop["_id"])
    return prop

@router.get("/properties")
async def get_all_properties(search: str = None):
    query = {}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    properties = list(db.properties.find(query))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties
# -------------------- Chat Endpoints --------------------

from fastapi import Form  # make sure Form is imported if not already

# Get or create chat for a property
@router.get("/chat/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user: dict = Depends(get_current_user)):
    chat = db.chats.find_one({"propertyId": property_id})
    if not chat:
        new_chat = {"propertyId": property_id, "messages": []}
        result = db.chats.insert_one(new_chat)
        new_chat["_id"] = str(result.inserted_id)
        return {"chatId": new_chat["_id"], "messages": []}
    
    # Convert ObjectId to str
    chat["_id"] = str(chat["_id"])
    return {"chatId": chat["_id"], "messages": chat["messages"]}

# Send message
@router.post("/chat/{chat_id}/send")
async def send_chat_message(chat_id: str, text: str = Form(...), current_user: dict = Depends(get_current_user)):
    chat = db.chats.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    message = {
        "sender": current_user["email"],
        "text": text,
        "timestamp": datetime.utcnow()
    }

    db.chats.update_one({"_id": ObjectId(chat_id)}, {"$push": {"messages": message}})
    return {"status": "ok", "message": message}

# Owner inbox: all chats for properties owned by this user
@router.get("/chat/inbox")
async def owner_inbox(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    # Find chats for properties owned by user
    properties = list(db.properties.find({"owner": user_email}, {"_id": 1}))
    property_ids = [str(p["_id"]) for p in properties]
    chats = list(db.chats.find({"propertyId": {"$in": property_ids}}))
    for c in chats:
        c["_id"] = str(c["_id"])
    return chats

# Get messages for specific chat
@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat = db.chats.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"messages": chat["messages"]}
#delete property

@router.delete("/property/{property_id}")
async def delete_property(
    property_id: str, 
    current_user: dict = Depends(get_current_user)
):
    # Find property
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    # Ensure only the owner can delete
    if prop["owner"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this property")

    # Delete property
    db.properties.delete_one({"_id": ObjectId(property_id)})

    # Optional: also delete related chat
    db.chats.delete_many({"propertyId": property_id})

    return {"message": "Property deleted successfully"}