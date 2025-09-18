from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from database import db
import cloudinary.uploader
from cloudinary_config import *
from routes.dependencies import get_current_user
from bson import ObjectId
from datetime import datetime
import json
from pydantic import BaseModel


router = APIRouter()

class ChatMessage(BaseModel):
    text: str

VALID_CATEGORIES = ["house", "villa", "apartment", "farmlands", "plots", "buildings"]



# ---------------- Add Property ----------------
@router.post("/add-property")
def add_property(
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(...),
    mobileNO: str = Form(...),
    images: list[UploadFile] = File(...),
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
        "latitude": latitude,
        "longitude": longitude,
        "category": category.lower(),
        "images": image_urls,
        "owner": current_user["email"],
        "ownerFullName": current_user.get("fullName", ""),
        "mobileNO": mobileNO,
        "created_at": datetime.utcnow()
    }

    result = db.properties.insert_one(property_data)
    property_data["_id"] = str(result.inserted_id)
    return {"message": "Property added successfully", "property": property_data}

# ---------------- Get My Properties ----------------
@router.get("/my-properties")
def get_my_properties(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    properties = list(db.properties.find({"owner": user_email}))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return {"properties": properties}

# ---------------- Get Property By ID ----------------
@router.get("/property/{property_id}")
def get_property_by_id(property_id: str):
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    prop["_id"] = str(prop["_id"])
    return prop

# ---------------- Get Properties By Category ----------------
@router.get("/category/{category}")
def get_properties_by_category(category: str, search: str = None):
    if category.lower() not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {VALID_CATEGORIES}")
    query = {"category": category.lower()}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    properties = list(db.properties.find(query))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties

# ---------------- Get All Properties ----------------
@router.get("/properties")
def get_all_properties(search: str = None):
    query = {}
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    properties = list(db.properties.find(query))
    for prop in properties:
        prop["_id"] = str(prop["_id"])
    return properties

# ---------------- Update Property ----------------
@router.put("/property/{property_id}")
def update_property(
    property_id: str,
    title: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(...),
    mobileNO: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    existingImages: str = Form("[]"),
    current_user: dict = Depends(get_current_user),
):
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop["owner"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing_images_list = json.loads(existingImages)
    image_urls = []

    for img in images:
        upload_result = cloudinary.uploader.upload(img.file, folder="real-estate-app", resource_type="auto")
        image_urls.append(upload_result.get("secure_url"))

    updated_data = {
        "title": title,
        "description": description,
        "price": price,
        "latitude": latitude,
        "longitude": longitude,
        "category": category.lower(),
        "mobileNO": mobileNO,
        "images": existing_images_list + image_urls,
    }

    db.properties.update_one({"_id": ObjectId(property_id)}, {"$set": updated_data})
    return {"message": "Property updated successfully"}

# ---------------- Delete Property ----------------
@router.delete("/property/{property_id}")
def delete_property(property_id: str, current_user: dict = Depends(get_current_user)):
    prop = db.properties.find_one({"_id": ObjectId(property_id)})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    if prop["owner"] != current_user["email"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete this property")

    db.properties.delete_one({"_id": ObjectId(property_id)})
    db.chats.delete_many({"propertyId": property_id})
    return {"message": "Property deleted successfully"}


# -------------------- Chat Endpoints --------------------

# ✅ Get or create chat for a property
@router.get("/chat/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user: dict = Depends(get_current_user)):
    try:
        prop = db.properties.find_one({"_id": ObjectId(property_id)})
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid property ID")

    property_id_str = str(property_id)
    chat = db.chats.find_one({"propertyId": property_id_str})

    if not chat:
        new_chat = {"propertyId": property_id_str, "messages": []}
        result = db.chats.insert_one(new_chat)
        return {
            "chat_id": str(result.inserted_id),
            "property_id": property_id_str,
            "messages": []
        }

    return {
        "chat_id": str(chat["_id"]),
        "property_id": chat["propertyId"],
        "messages": chat.get("messages", [])
    }

#send message
@router.post("/chat/{chat_id}/send")
async def send_chat_message(
    chat_id: str,
    payload: ChatMessage,   # 👈 use the Pydantic model
    current_user: dict = Depends(get_current_user),
):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    message = {
        "sender": current_user["email"],
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
    }

    result = db.chats.update_one(   # 👈 no await, use db.chats
        {"_id": ObjectId(chat_id)},
        {"$push": {"messages": message}},
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")

    return {"message": "Message sent", "data": message}


# ✅ Owner inbox (normalized response)
@router.get("/chat/inbox")
async def owner_inbox(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    # Find properties owned by this user
    properties = list(db.properties.find({"owner": user_email}, {"_id": 1}))
    property_ids = [str(p["_id"]) for p in properties]

    if not property_ids:
        return []

    chats = list(db.chats.find({"propertyId": {"$in": property_ids}}))

    formatted_chats = []
    for c in chats:
        messages = c.get("messages", [])
        last_message = messages[-1] if messages else None

        # Count unread messages (basic version)
        unread_count = sum(1 for m in messages if m["sender"] != user_email)

        formatted_chats.append({
            "chat_id": str(c["_id"]),
            "property_id": c["propertyId"],
            "user_name": (last_message["sender"] if last_message else "Unknown"),
            "last_message": last_message,
            "unread_count": unread_count
        })

    return formatted_chats

# ✅ Get messages for a specific chat
@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    try:
        chat = db.chats.find_one({"_id": ObjectId(chat_id)})
        if not chat:
            raise HTTPException(status_code=404, detail="Chat not found")
    except:
        raise HTTPException(status_code=400, detail="Invalid chat ID")

    return {
        "chat_id": str(chat["_id"]),
        "property_id": chat["propertyId"],
        "messages": chat.get("messages", [])
    }
