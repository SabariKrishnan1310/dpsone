import os
import json
import redis
from fastapi import FastAPI, Depends, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from datetime import datetime, timezone 
import json
from sqlalchemy.orm import Session
from models import AttendanceLog, get_db, create_tables 
import redis.asyncio as aioredis
import asyncio
import httpx


app = FastAPI(title="DPS ONE Ingestion API (Phase 1)")


REDIS_HOST = os.environ.get("REDIS_HOST")

sync_redis = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)

async def get_async_redis_client():
    return aioredis.from_url(f"redis://{REDIS_HOST}:6379", decode_responses=True)



class TapData(BaseModel):
    rfid_uid: str
    device_id: str
    status: str = "IN" 

    
    school_id: str
    location: str | None = None
    
    cur_time: datetime = Field(alias="current_time", default_factory=lambda: datetime.now(timezone.utc)) 
    role: str = "STUDENT"
    


@app.on_event("startup")
def on_startup():
    
    create_tables()


@app.get("/")
def read_root():
    return {"status": "Ingestion API Running", "message": "Ready to receive taps."}


@app.post("/iot/tap", status_code=status.HTTP_202_ACCEPTED)
def receive_tap(data: TapData, db: Session = Depends(get_db)):
    """
    Receives an RFID tap, looks up user details from Django (Data Enrichment),
    logs the enriched data to PostgreSQL, and publishes to Redis.
    """
    DJANGO_LOOKUP_URL = f"http://nginx/api/v1/lookup/{data.rfid_uid}/"
    try:
        response = httpx.get(DJANGO_LOOKUP_URL)
        response.raise_for_status() 
        enriched_data = response.json()
        data.school_id = enriched_data.get('school_id', data.school_id)
        data.role = enriched_data.get('role', data.role)
        
    except httpx.HTTPStatusError as e:
        
        print(f"ERROR: Lookup failed for {data.rfid_uid}. HTTP Status: {e.response.status_code}. Using fallback data.")
        
        
        
    except httpx.RequestError as e:
        
        print(f"FATAL ERROR: Could not connect to Django Management API: {e}. Using fallback data.")
        

    
    new_log = AttendanceLog(
        rfid_uid=data.rfid_uid,
        device_id=data.device_id,
        status=data.status,
        
        
        school_id=data.school_id, 
        location=data.location,
        role=data.role,
        current_time=data.cur_time,
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log) 

    
    realtime_data = {
        "log_id": new_log.log_id,
        "uid": data.rfid_uid,
        "status": data.status,
        
        
        "school": data.school_id,
        "location": data.location,
        "role": data.role,
        "tap_time": new_log.current_time.isoformat(), 
        
        "device": data.device_id,
        "db_time": new_log.timestamp.isoformat()
    }
    
    sync_redis.publish('live_attendance', json.dumps(realtime_data))
    
    return {"message": "Tap recorded and published", "log_id": new_log.log_id}



@app.websocket("/ws/live-dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        redis_client = await get_async_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('live_attendance')
        
        await websocket.send_text(json.dumps({"message": "Subscription started. Waiting for taps..."}))
        
        
        async for message in pubsub.listen():
            if message and message['type'] == 'message':
                
                try:
                    
                    await websocket.send_text(message['data'])
                except Exception as e:
                    print(f"Error sending message to client: {e}")
            
    except WebSocketDisconnect:
        print(f"Client disconnected from WebSocket.")
    except Exception as e:
        print(f"WebSocket error: {e}")
        
    finally:
        if 'pubsub' in locals() and pubsub:
            await pubsub.unsubscribe('live_attendance')
        if 'redis_client' in locals() and redis_client:
            await redis_client.close()
