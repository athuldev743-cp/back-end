from fastapi import APIRouter, Body, Depends, HTTPException
from pymongo import MongoClient
from datetime import datetime
from routes.auth import get_current_user

router = APIRouter()

# ---------------- Database ----------------
MONGO_URI = "your_mongo_uri_here"  # replace with actual URI or use os.getenv
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# ---------------- REST: Get or create chat for a property ----------------
@router.get("/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    # Check if chat already exists for this property and user
    chat_doc = chats_collection.find_one({
        "property_id": property_id,
        "participants": {"$in": [user_email]}
    })

    if not chat_doc:
        # Create new chat
        chat_id = f"{property_id}_{user_email}_{int(datetime.utcnow().timestamp())}"
        chat_doc = {
            "chat_id": chat_id,
            "property_id": property_id,
            "participants": [user_email],  # Owner can be added later if needed
            "messages": [],
            "last_message": None
        }
        chats_collection.insert_one(chat_doc)

    return {"chatId": chat_doc["chat_id"], "messages": chat_doc.get("messages", [])}


# ---------------- REST: Send message ----------------
@router.post("/{chat_id}/send")
async def send_message_rest(
    chat_id: str,
    text: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    user_email = current_user["email"]

    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Ensure sender is in participants
    if user_email not in chat_doc.get("participants", []):
        chats_collection.update_one(
            {"chat_id": chat_id},
            {"$push": {"participants": user_email}}
        )

    msg = {
        "sender": user_email,
        "text": text,
        "read": False,
        "timestamp": datetime.utcnow().timestamp()
    }

    # Save message and update last_message
    chats_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"messages": msg}, "$set": {"last_message": msg}}
    )

    return {"status": "ok", "message": msg}


# ---------------- REST: Get all chats for owner (Inbox) ----------------
@router.get("/inbox")
async def get_owner_inbox(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    chats_cursor = chats_collection.find({"participants": {"$in": [user_email]}})
    inbox = []
    async for chat in chats_cursor:
        inbox.append({
            "chat_id": chat["chat_id"],
            "property_id": chat["property_id"],
            "last_message": chat.get("last_message"),
            "unread_count": sum(1 for m in chat.get("messages", []) if not m.get("read", False) and m.get("sender") != user_email)
        })

    return {"inbox": inbox}


# ---------------- REST: Mark messages as read ----------------
@router.post("/mark-read/{chat_id}")
async def mark_messages_as_read(chat_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Mark messages as read for this user
    updated_messages = [
        {**m, "read": True} if m.get("sender") != user_email else m
        for m in chat_doc.get("messages", [])
    ]

    chats_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {"messages": updated_messages}}
    )

    return {"status": "ok"}
