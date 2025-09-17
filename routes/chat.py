# chat.py
from typing import List, Dict
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from routes.dependencies import get_current_user
import os
from datetime import datetime
from bson import ObjectId

router = APIRouter()

MONGO_URI = os.getenv("MONGO_URI", "your_mongo_uri_here")
client = AsyncIOMotorClient(MONGO_URI)
db = client.real_estate

chats_collection = db.chats
properties_collection = db.properties

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, chat_id: str, websocket: WebSocket):
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, chat_id: str, websocket: WebSocket):
        if chat_id in self.active_connections and websocket in self.active_connections[chat_id]:
            self.active_connections[chat_id].remove(websocket)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, chat_id: str, message: dict):
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                await connection.send_json(message)

manager = ConnectionManager()

# REST API: add property
@router.post("/add-property")
async def add_property(data: dict, current_user=Depends(get_current_user)):
    try:
        owner_email = current_user["email"]
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_property = {
        "title": data.get("title", ""),
        "category": data.get("category", ""),
        "location": data.get("location", ""),
        "description": data.get("description", ""),
        "owner_email": owner_email,
        "created_at": datetime.utcnow()
    }
    result = await properties_collection.insert_one(new_property)
    new_property["_id"] = str(result.inserted_id)
    return new_property

# REST API: get or create chat
@router.get("/property/{property_id}")
async def get_or_create_chat(property_id: str, current_user=Depends(get_current_user)):
    try:
        user_email = current_user["email"]
    except Exception:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        prop_oid = ObjectId(property_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid property ID")

    property_doc = await properties_collection.find_one({"_id": prop_oid})
    if not property_doc:
        raise HTTPException(status_code=404, detail="Property not found")

    owner_email = property_doc.get("owner_email", user_email)
    if owner_email == user_email:
        raise HTTPException(status_code=400, detail="Cannot chat with your own property")

    chat_doc = await chats_collection.find_one({
        "property_id": property_id,
        "participants": {"$all": [user_email, owner_email]}
    })

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
        await chats_collection.insert_one(chat_doc)

    return {"chatId": chat_doc["chat_id"], "messages": chat_doc.get("messages", [])}

# WebSocket endpoint
@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str, current_user=Depends(get_current_user)):
    try:
        user_email = current_user["email"]
    except Exception:
        await websocket.close(code=1008)
        return

    chat_doc = await chats_collection.find_one({"chat_id": chat_id})
    if not chat_doc or user_email not in chat_doc["participants"]:
        await websocket.close(code=1008)
        return

    await manager.connect(chat_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            message_text = data.get("text")
            if not message_text:
                continue

            new_message = {
                "sender": user_email,
                "text": message_text,
                "timestamp": datetime.utcnow(),
                "read": False
            }

            await chats_collection.update_one(
                {"chat_id": chat_id},
                {"$push": {"messages": new_message}, "$set": {"last_message": new_message}}
            )

            await manager.broadcast(chat_id, {"new_message": new_message})
    except WebSocketDisconnect:
        manager.disconnect(chat_id, websocket)
    except Exception:
        manager.disconnect(chat_id, websocket)
