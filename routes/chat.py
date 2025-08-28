from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pymongo import MongoClient
import asyncio
import redis.asyncio as aioredis
import os
from dotenv import load_dotenv
from jose import jwt, JWTError
import json

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

# ---------------- Connected clients ----------------
connected_clients = {}  # chat_id -> { user_email: websocket }

# ---------------- Auth helper ----------------
def get_user_from_token(token: str):
    from routes.auth import SECRET_KEY, ALGORITHM
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("email")
        if not email:
            return None
        user = db.users.find_one({"email": email})
        return user
    except JWTError:
        return None

# ---------------- WebSocket ----------------
@router.websocket("/ws/{chat_id}/{property_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: str,
    property_id: str,
    token: str = Query(...)
):
    user = get_user_from_token(token)
    if not user:
        await websocket.close(code=1008)
        return

    user_email = user["email"]
    await websocket.accept()

    # Register client
    if chat_id not in connected_clients:
        connected_clients[chat_id] = {}
    connected_clients[chat_id][user_email] = websocket

    # Send previous messages
    chat_doc = chats_collection.find_one({"chat_id": chat_id})
    if chat_doc:
        for msg in chat_doc.get("messages", []):
            await websocket.send_json(msg)

    # Redis pub/sub
    redis_conn = await get_redis()
    pubsub = redis_conn.pubsub()
    await pubsub.subscribe(chat_id)

    async def redis_listener():
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    msg_json = json.loads(message["data"].decode())
                except json.JSONDecodeError:
                    continue
                for uid, client_ws in connected_clients.get(chat_id, {}).items():
                    if uid != msg_json.get("sender") and client_ws.application_state == WebSocket.STATE_CONNECTED:
                        await client_ws.send_json(msg_json)

    listener_task = asyncio.create_task(redis_listener())

    try:
        while True:
            data = await websocket.receive_json()
            msg = {
                "sender": user_email,
                "text": data.get("text", ""),
                "read": False
            }

            # Save in MongoDB
            chats_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {"property_id": property_id}, "$push": {"messages": msg}},
                upsert=True
            )

            # Publish to Redis
            await redis_conn.publish(chat_id, json.dumps(msg))

            # Send to local clients
            for uid, client_ws in connected_clients.get(chat_id, {}).items():
                if uid != user_email and client_ws.application_state == WebSocket.STATE_CONNECTED:
                    await client_ws.send_json(msg)

    except WebSocketDisconnect:
        print(f"{user_email} disconnected from chat {chat_id}")
    finally:
        listener_task.cancel()
        if chat_id in connected_clients and user_email in connected_clients[chat_id]:
            del connected_clients[chat_id][user_email]
        if chat_id in connected_clients and not connected_clients[chat_id]:
            del connected_clients[chat_id]
        await pubsub.unsubscribe(chat_id)

# ---------------- Inbox & Notifications ----------------
@router.get("/inbox")
def get_owner_inbox():
    # Import here to avoid circular import
    from routes.auth import get_current_user
    from fastapi import Depends
    current_user = Depends(get_current_user)()
    owner_email = current_user["email"]

    chats = list(chats_collection.find({"property_owner": owner_email}))

    inbox = []
    for chat in chats:
        last_msg = chat["messages"][-1] if chat.get("messages") else None
        unread_count = sum(
            1 for m in chat.get("messages", [])
            if not m.get("read", True) and m.get("sender") != owner_email
        )
        inbox.append({
            "chat_id": chat["chat_id"],
            "property_id": chat["property_id"],
            "last_message": last_msg,
            "unread_count": unread_count
        })

    # Sort inbox by last message time (newest first)
    inbox.sort(key=lambda x: x["last_message"]["timestamp"] if x["last_message"] else 0, reverse=True)
    return {"inbox": inbox}

@router.post("/mark-read/{chat_id}")
def mark_messages_as_read(chat_id: str):
    from routes.auth import get_current_user
    from fastapi import Depends
    current_user = Depends(get_current_user)()
    owner_email = current_user["email"]

    chats_collection.update_one(
        {"chat_id": chat_id, "property_owner": owner_email},
        {"$set": {"messages.$[elem].read": True}},
        array_filters=[{"elem.read": False, "elem.sender": {"$ne": owner_email}}]
    )
    return {"status": "ok"}
