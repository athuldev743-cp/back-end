from fastapi import APIRouter
from pymongo import MongoClient
import os

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# Fetch unread chat notifications for a user (owner)
@router.get("/notifications/{owner_id}")
def get_unread_chats(owner_id: str):
    chats = chats_collection.find({"property_owner": owner_id, "messages.read": False})
    result = []
    for chat in chats:
        unread_count = sum(1 for m in chat.get("messages", []) if not m.get("read", True))
        if unread_count > 0:
            result.append({
                "chat_id": chat["chat_id"],
                "property_id": chat["property_id"],
                "unread_count": unread_count
            })
    return {"notifications": result}

# Mark chat messages as read
@router.post("/mark-read/{chat_id}/{owner_id}")
def mark_messages_as_read(chat_id: str, owner_id: str):
    chats_collection.update_one(
        {"chat_id": chat_id, "property_owner": owner_id},
        {"$set": {"messages.$[].read": True}}
    )
    return {"status": "ok"}
