from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from routes.dependencies import get_current_user
import os

router = APIRouter()

# -------------------- MongoDB Setup --------------------
MONGO_URI = os.getenv("MONGO_URI", "your_mongo_uri_here")
client = AsyncIOMotorClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# -------------------- Get Unread Notifications --------------------
@router.get("/notifications")
async def get_unread_chats(current_user=Depends(get_current_user)):
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

    cursor = chats_collection.find(
        {
            "participants": user_email,
            "messages": {"$elemMatch": {"read": False, "sender": {"$ne": user_email}}}
        },
        {"chat_id": 1, "property_id": 1, "messages": 1}
    )
    chats = await cursor.to_list(100)

    result = []
    for chat in chats:
        unread_count = sum(
            1 for m in chat.get("messages", [])
            if not m.get("read", True) and m.get("sender") != user_email
        )
        if unread_count > 0:
            result.append({
                "chat_id": str(chat.get("chat_id")),
                "property_id": chat.get("property_id"),
                "unread_count": unread_count
            })

    return {"notifications": result}

# -------------------- Mark Messages as Read --------------------
@router.post("/mark-read/{chat_id}")
async def mark_messages_as_read(chat_id: str, current_user=Depends(get_current_user)):
    user_email = current_user.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="User email not found")

    query = {"chat_id": chat_id, "participants": user_email}

    result = await chats_collection.update_one(
        query,
        {"$set": {"messages.$[elem].read": True}},
        array_filters=[{"elem.read": False, "elem.sender": {"$ne": user_email}}]
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No unread messages found")

    return {"status": "ok"}
