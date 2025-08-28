from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from pymongo import MongoClient
import asyncio
import redis.asyncio as aioredis
import os
from dotenv import load_dotenv
from routes.auth import get_current_user

load_dotenv()
router = APIRouter()

# ---------------- Database ----------------
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# ---------------- Redis ----------------
REDIS_URI = os.getenv("REDIS_URI")
redis_conn_instance = None

async def get_redis():
    global redis_conn_instance
    if not redis_conn_instance:
        redis_conn_instance = await aioredis.from_url(REDIS_URI)
    return redis_conn_instance

# ---------------- Connected Clients ----------------
connected_clients = {}

# ---------------- WebSocket Endpoint ----------------
@router.websocket("/ws/{chat_id}/{user_id}/{property_id}/{owner_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str, user_id: str, property_id: str, owner_id: str):
    await websocket.accept()

    if chat_id not in connected_clients:
        connected_clients[chat_id] = {}
    connected_clients[chat_id][user_id] = websocket

    # Send previous messages
    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if chat_doc:
        for msg in chat_doc.get("messages", []):
            await websocket.send_text(f"{msg['sender']}: {msg['text']}")

    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(chat_id)

    async def redis_listener():
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"].decode()
                for uid, client_ws in connected_clients.get(chat_id, {}).items():
                    if client_ws != websocket:
                        await client_ws.send_text(data)

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            data = await websocket.receive_text()

            # Save message in MongoDB with unread flag
            chats_collection.update_one(
                {"chat_id": chat_id},
                {
                    "$set": {"property_id": property_id, "property_owner": owner_id},
                    "$push": {
                        "messages": {
                            "sender": user_id,
                            "text": data,
                            "read": False
                        }
                    },
                },
                upsert=True
            )

            # Publish to Redis
            await redis_conn.publish(chat_id, f"{user_id}: {data}")

            # Send to local clients
            for uid, client_ws in connected_clients.get(chat_id, {}).items():
                if uid != user_id:
                    await client_ws.send_text(f"{user_id}: {data}")

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected from chat {chat_id}")
    finally:
        listener_task.cancel()
        if chat_id in connected_clients and user_id in connected_clients[chat_id]:
            del connected_clients[chat_id][user_id]
        if chat_id in connected_clients and not connected_clients[chat_id]:
            del connected_clients[chat_id]
        await pubsub.unsubscribe(chat_id)

# ---------------- Notifications (for owner) ----------------
@router.get("/notifications")
def get_unread_chats(current_user: dict = Depends(get_current_user)):
    owner_id = current_user["email"]
    chats = chats_collection.find(
        {"property_owner": owner_id, "messages.read": False},
        {"chat_id": 1, "property_id": 1, "messages": 1}
    )
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
