from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from routes.auth import get_current_user
from database import db

router = APIRouter()

# Collections
properties_collection = db["properties"]
chats_collection = db["chats"]

# ---------------- GET OR CREATE CHAT ----------------
@router.get("/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    # Get property to find owner email
    property_doc = properties_collection.find_one({"_id": property_id})
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not found")

    owner_email = property_doc.get("owner_email")
    if not owner_email:
        raise HTTPException(status_code=400, detail="Property owner not set")

    # Check if chat already exists between this buyer + owner for the property
    chat_doc = chats_collection.find_one({
        "property_id": property_id,
        "participants": {"$all": [user_email, owner_email]}
    })

    if not chat_doc:
        chat_id = f"{property_id}_{user_email}_{int(datetime.utcnow().timestamp())}"
        chat_doc = {
            "chat_id": chat_id,
            "property_id": property_id,
            "participants": [user_email, owner_email],   # buyer + owner
            "property_owner": owner_email,              # 🔑 for notifications
            "messages": [],
            "last_message": None
        }
        chats_collection.insert_one(chat_doc)

    return {
        "chatId": chat_doc["chat_id"],
        "messages": chat_doc.get("messages", [])
    }


# ---------------- INBOX ROUTE ----------------
@router.get("/inbox")
async def get_inbox(current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    # Fetch all chats where user is either buyer or owner
    chats = list(chats_collection.find(
        {"participants": user_email},  # either buyer or owner
        {"_id": 0}
    ))

    return {"chats": chats}


# ---------------- SEND MESSAGE ----------------
@router.post("/chat/{chat_id}/send")
async def send_message(chat_id: str, text: str, current_user: dict = Depends(get_current_user)):
    user_email = current_user["email"]

    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc:
        raise HTTPException(status_code=404, detail="Chat not found")

    message = {
        "sender": user_email,
        "text": text,
        "timestamp": datetime.utcnow(),
        "read": False
    }

    chats_collection.update_one(
        {"chat_id": chat_id},
        {
            "$push": {"messages": message},
            "$set": {"last_message": message}
        }
    )

    return {"status": "Message sent"}
