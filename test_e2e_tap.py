import requests
import hashlib

unit_id = "3516281f-f57d-4924-a511-2143a05ae2f7"
raw_hex = "ABCD1234EF"

# 1. We assume the Identity has been created or we just warm the redis cache directly for testing
# Actually, let's just insert into redis
import redis
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

hashed = hashlib.sha256(raw_hex.encode()).hexdigest()
print(f"Hashed RFID: {hashed}")

# Insert unit into redis
r.hset(f"cache:unit:{unit_id}", mapping={
    "unit_id": unit_id,
    "org_id": "test-org",
    "vertical": "SCHOOL"
})

# Insert user into redis
r.hset(f"cache:rfid:{hashed}", mapping={
    "user_id": "user-1234",
    "primary_unit_id": unit_id,
    "name": "Tim Cook",
    "role": "Executive"
})

# 2. Curl the endpoint
print("Cache warmed. Sending POST to ingestion API...")
resp = requests.post(
    "http://localhost:8000/ingest/v2/tap/",
    json={"raw_hex": raw_hex, "device_id": "Scanner_01"},
    headers={"X-Unit-ID": unit_id}
)

print("Response:", resp.status_code, resp.text)
