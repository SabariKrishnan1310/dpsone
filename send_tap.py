import requests
import time
import hashlib

url = 'http://localhost:8000/ingest/v2/tap'
hashed = hashlib.sha256("TEST_RFID_123".encode()).hexdigest()
data = {
    "device_id": "READER_01",
    "unit_id": "19fd23cf-7f56-4f5f-91a8-5c43bd4ee60b",
    "hashed_rfid": hashed,
    "timestamp": str(int(time.time())),
    "direction": "IN"
}
headers = {
    "X-Unit-ID": "19fd23cf-7f56-4f5f-91a8-5c43bd4ee60b"
}
response = requests.post(url, json=data, headers=headers)
print(response.status_code, response.text)
