from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pymongo import MongoClient
import asyncio
import redis.asyncio as aioredis
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file

router = APIRouter()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")  
client = MongoClient(MONGO_URI)
db = client.real_estate
chats_collection = db.chats

# Redis connection instance
REDIS_URI = os.getenv("REDIS_URI")  
redis_conn_instance = None

async def get_redis():
    global redis_conn_instance
    if not redis_conn_instance:
        redis_conn_instance = await aioredis.from_url(REDIS_URI)
    return redis_conn_instance

# Local WebSocket connections per chat
connected_clients = {}

@router.websocket("/ws/{chat_id}/{user_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: str, user_id: str):
    await websocket.accept()

    if chat_id not in connected_clients:
        connected_clients[chat_id] = {}
    connected_clients[chat_id][user_id] = websocket

    # Send previous messages from MongoDB
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

            # Save message in MongoDB
            chats_collection.update_one(
                {"chat_id": chat_id},
                {"$push": {"messages": {"sender": user_id, "text": data}}},
                upsert=True
            )

            # Publish message to Redis channel
            await redis_conn.publish(chat_id, f"{user_id}: {data}")

            # Send to local clients immediately
            for uid, client_ws in connected_clients.get(chat_id, {}).items():
                if uid != user_id:
                    await client_ws.send_text(f"{user_id}: {data}")

    except WebSocketDisconnect:
        print(f"User {user_id} disconnected from chat {chat_id}")
    except Exception as e:
        print(f"Error in WebSocket chat {chat_id} for user {user_id}: {e}")
    finally:
        listener_task.cancel()
        if chat_id in connected_clients and user_id in connected_clients[chat_id]:
            del connected_clients[chat_id][user_id]
        if chat_id in connected_clients and not connected_clients[chat_id]:
            del connected_clients[chat_id]
        await pubsub.unsubscribe(chat_id)
