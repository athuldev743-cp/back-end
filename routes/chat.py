from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Body, Depends
from pymongo import MongoClient
import redis.asyncio as aioredis
import asyncio, json
from datetime import datetime
from dotenv import load_dotenv
from jose import jwt, JWTError
from routes.auth import get_current_user

load_dotenv()
router = APIRouter()

# ---------------- Database ----------------
MONGO_URI = "your_mongo_uri_here"  # replace with actual URI or use os.getenv
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# ---------------- Redis ----------------
REDIS_URI = "your_redis_uri_here"  # replace with actual URI or use os.getenv
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
                msg_json = json.loads(message["data"].decode())
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
                "read": False,
                "timestamp": datetime.utcnow().timestamp()
            }

            # Save in MongoDB
            chats_collection.update_one(
                {"chat_id": chat_id},
                {"$set": {"property_id": property_id, "last_message": msg}, "$push": {"messages": msg}},
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
        connected_clients.get(chat_id, {}).pop(user_email, None)
        await pubsub.unsubscribe(chat_id)

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
            "participants": [user_email],  # Owner can be added later
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
        return {"error": "Chat not found"}

    msg = {
        "sender": user_email,
        "text": text,
        "read": False,
        "timestamp": datetime.utcnow().timestamp()
    }

    chats_collection.update_one(
        {"chat_id": chat_id},
        {"$push": {"messages": msg}, "$set": {"last_message": msg}},
        upsert=True
    )

    redis_conn = await get_redis()
    await redis_conn.publish(chat_id, json.dumps(msg))

    return {"status": "ok", "message": msg}
