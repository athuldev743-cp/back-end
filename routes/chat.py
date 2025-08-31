from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel
from routes.auth import get_current_user
from database import db

router = APIRouter()

# Collections
properties_collection = db["properties"]
chats_collection = db["chats"]

# ---------------- Pydantic models ----------------
class PropertyIn(BaseModel):
    title: str
    category: str
    location: str
    description: str = ""

class MessageIn(BaseModel):
    text: str

# ---------------- ADD PROPERTY ----------------
@router.post("/add-property")
async def add_property(data: PropertyIn, current_user: dict = Depends(get_current_user)):
    owner_email = current_user["email"]

    new_property = {
        "title": data.title,
        "category": data.category,
        "location": data.location,
        "description": data.description,
        "owner_email": owner_email,
        "created_at": datetime.utcnow()
    }

    result = properties_collection.insert_one(new_property)
    new_property["_id"] = str(result.inserted_id)
    return new_property

# ---------------- GET OR CREATE CHAT ----------------
@router.get("/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    # Convert property_id string to ObjectId
    try:
        prop_oid = ObjectId(property_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid property ID")

    property_doc = properties_collection.find_one({"_id": prop_oid})
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not found")

    # Ensure owner_email exists
    owner_email = property_doc.get("owner_email")
    if not owner_email:
        # If missing, fallback to current user as owner
        owner_email = user_email
        properties_collection.update_one(
            {"_id": prop_oid},
            {"$set": {"owner_email": owner_email}}
        )

    # Prevent user from chatting with self
    if owner_email == user_email:
        raise HTTPException(status_code=400, detail="Cannot chat with your own property")

    # Check if chat exists
    chat_doc = chats_collection.find_one({
        "property_id": property_id,
        "participants": {"$all": [user_email, owner_email]}
    })

    # If not, create new chat
    if not chat_doc:
        chat_id = f"{property_id}_{user_email}_{int(datetime.utcnow().timestamp())}"
        chat_doc = {
            "chat_id": chat_id,
            "property_id": property_id,
            "participants": [user_email, owner_email],
            "property_owner": owner_email,
            "messages": [],
            "last_message": None
        }
        chats_collection.insert_one(chat_doc)

    return {"chatId": chat_doc["chat_id"], "messages": chat_doc.get("messages", [])}

# ---------------- SEND MESSAGE ----------------
@router.post("/chat/{chat_id}/send")
async def send_message(chat_id: str, message: MessageIn, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    new_message = {
        "sender": user_email,
        "text": message.text,
        "timestamp": datetime.utcnow(),
        "read": False
    }

    chats_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"messages": new_message}, "$set": {"last_message": new_message}}
    )

    return {"status": "Message sent"}

# ---------------- OWNER INBOX ----------------
@router.get("/inbox")
async def get_inbox(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    chats = list(chats_collection.find({"participants": user_email}, {"_id": 0}))
    return {"chats": chats}

# ---------------- GET CHAT MESSAGES ----------------
@router.get("/chat/{chat_id}/messages")
async def get_chat_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"messages": chat_doc.get("messages", [])}

# ---------------- MARK MESSAGES AS READ ----------------
@router.post("/chat/mark-read/{chat_id}")
async def mark_messages_as_read(chat_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]
    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    updated_messages = [
        {**msg, "read": True} if msg["sender"] != user_email else msg
        for msg in chat_doc.get("messages", [])
    ]

    chats_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"messages": updated_messages}}
    )

    return {"status": "Messages marked as read"}
