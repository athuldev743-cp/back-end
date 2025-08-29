# routes/chat_notifications.py
from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from bson import ObjectId
from routes.dependencies import get_current_user
import os

router = APIRouter()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI") or "your_mongo_uri_here"
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# ---------------- GET unread notifications ----------------
@router.get("/notifications")
def get_unread_chats(current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    owner_email = current_user.get("email")
    if not owner_email:
        raise HTTPException(status_code=400, detail="User email not found")

    try:
        chats = list(chats_collection.find(
            {"property_owner": owner_email, "messages": {"$elemMatch": {"read": False}}},
            {"chat_id": 1, "property_id": 1, "messages": 1}
        ))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    result = []
    for chat in chats:
        unread_count = sum(1 for m in chat.get("messages", []) if not m.get("read", True))
        if unread_count > 0:
            result.append({
                "chat_id": str(chat.get("chat_id") or chat.get("_id")),
                "property_id": chat.get("property_id"),
                "unread_count": unread_count
            })

    return {"notifications": result}

# ---------------- POST mark messages as read ----------------
@router.post("/mark-read/{chat_id}")
def mark_messages_as_read(chat_id: str, current_user: dict = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    owner_email = current_user.get("email")
    if not owner_email:
        raise HTTPException(status_code=400, detail="User email not found")

    query = {
        "$or": [
            {"chat_id": chat_id},
            {"_id": ObjectId(chat_id)} if ObjectId.is_valid(chat_id) else {}
        ],
        "property_owner": owner_email
    }

    try:
        result = chats_collection.update_one(
            query,
            {"$set": {"messages.$[elem].read": True}},
            array_filters=[{"elem.read": False, "elem.sender": {"$ne": owner_email}}]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No unread messages found")

    return {"status": "ok"}
