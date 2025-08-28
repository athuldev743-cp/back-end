from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from routes.dependencies import get_current_user  # 👈 fix import
import os

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# ---------------- Unread chat notifications ----------------
@router.get("/notifications")
def get_unread_chats(current_user: dict = Depends(get_current_user)):
    owner_id = current_user.get("email")
    if not owner_id:
        raise HTTPException(status_code=400, detail="User email not found")

    chats = chats_collection.find(
        {"property_owner": owner_id, "messages.read": False},
        {"chat_id": 1, "property_id": 1, "messages": 1}
    )

    result = []
    for chat in chats:
        messages = chat.get("messages", [])
        unread_count = sum(1 for m in messages if not m.get("read", True))
        if unread_count > 0:
            result.append({
                "chat_id": chat.get("chat_id"),
                "property_id": chat.get("property_id"),
                "unread_count": unread_count
            })
    return {"notifications": result}


# ---------------- Mark messages as read ----------------
@router.post("/mark-read/{chat_id}")
def mark_messages_as_read(chat_id: str, current_user: dict = Depends(get_current_user)):
    owner_id = current_user["email"]
    chats_collection.update_one(
        {"chat_id": chat_id, "property_owner": owner_id},
        {"$set": {"messages.$[elem].read": True}},
        array_filters=[{"elem.read": False, "elem.sender": {"$ne": owner_id}}]
    )
    return {"status": "ok"}
