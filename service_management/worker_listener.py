import os
import json
import redis
import time
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dps_core.settings')
django.setup() 

from student_management.tasks import process_tap_from_queue

REDIS_HOST = os.environ.get("REDIS_HOST", "redis") 
REDIS_CHANNEL = 'live_attendance'

def start_worker_listener():
    """Monitors the Redis Pub/Sub channel and dispatches taps to the Celery queue."""
    print(f"Starting Worker Listener for channel: {REDIS_CHANNEL}...")
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
        pubsub = r.pubsub()
        pubsub.subscribe(REDIS_CHANNEL)
        print("Connected to Redis. Listening for new taps...")
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                tap_data_json = message['data']
                print(f"Ingested tap received. Queueing for processing...")
                
                process_tap_from_queue.delay(tap_data_json)
                
    except redis.exceptions.ConnectionError as e:
        print(f"FATAL ERROR: Could not connect to Redis: {e}. Retrying in 5s.")
        time.sleep(5)
        start_worker_listener() 
    except Exception as e:
        print(f"An unexpected error occurred in listener: {e}")

if __name__ == '__main__':
    start_worker_listener()
