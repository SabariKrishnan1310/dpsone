import requests
import random
import json
from datetime import datetime, timezone
import os

# --- CONFIG ---
API_URL = "http://localhost:8000/iot/tap"  # FastAPI endpoint
RFID_COUNT = 50  # Number of RFID tags to simulate (matches demo_data.py)
TAPS_PER_RFID = 1  # Number of taps per RFID

# --- Generate the same RFID tag IDs as demo_data.py ---
def generate_rfids():
    rfids = [f"RFID{i}school-1" for i in range(1, RFID_COUNT + 1)]
    return rfids

# --- Main stress test ---
def main():
    rfids = generate_rfids()
    for rfid_uid in rfids:
        for _ in range(TAPS_PER_RFID):
            payload = {
                "rfid_uid": rfid_uid,
                "device_id": f"device_{random.randint(1,5)}",
                "status": random.choice(["IN", "OUT"]),
                "school_id": "school-1",
                "location": random.choice(["Main Gate", "Library", "Canteen"]),
                "current_time": datetime.now(timezone.utc).isoformat(),
                "role": "STUDENT"
            }
            try:
                resp = requests.post(API_URL, json=payload, timeout=3)
                print(f"{rfid_uid} -> {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"{rfid_uid} -> ERROR: {e}")

if __name__ == "__main__":
    main()
