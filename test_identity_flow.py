import requests
import hashlib
import time

# First login to get session
url_login = 'http://localhost:8001/edu/login/'
client = requests.session()

# get CSRF token
client.get(url_login)
csrftoken = client.cookies.get('csrftoken')

if not csrftoken:
    print("Could not get CSRF token")
    exit(1)

data = {
    'username': 'sabari',
    'password': '1234',
    'csrfmiddlewaretoken': csrftoken
}
headers = {'Referer': url_login}
response = client.post(url_login, data=data, headers=headers)
print("Login status:", response.status_code)

if not response.url.endswith('/edu/'):
    print("Login failed. Current URL:", response.url)
    exit(1)

print("Redirected to dashboard successfully")

# Now test identity creation via POST to /edu/identity/
identity_url = 'http://localhost:8001/edu/identity/'

# Get the form again to get fresh CSRF token (since we're on a new page)
identity_page = client.get(identity_url)
if identity_page.status_code != 200:
    print("Failed to get identity form page:", identity_page.status_code)
    exit(1)

# Extract CSRF token from the form
import re
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', identity_page.text)
if csrf_match:
    csrf_token = csrf_match.group(1)
    print("Got CSRF token for identity form")
else:
    # Fallback to using the session's csrftoken
    csrf_token = client.cookies.get('csrftoken')
    print("Using session CSRF token")

# Prepare identity data
test_username = f'testuser_{int(time.time())}'
test_email = f'{test_username}@test.com'
test_role = 'TEACHER'
test_unit = '3516281f-f57d-4924-a511-2143a05ae2f7'  # From our test_setup.py
test_rfid = f'TEST_CARD_{int(time.time())}'

identity_data = {
    'username': test_username,
    'email': test_email,
    'role_type': test_role,
    'unit_id': test_unit,
    'raw_rfid': test_rfid,
    'csrfmiddlewaretoken': csrf_token
}

print(f"Creating identity: {test_username}")
print(f"Email: {test_email}")
print(f"Role: {test_role}")
print(f"Unit: {test_unit}")
print(f"Raw RFID: {test_rfid}")

# Submit the form
identity_response = client.post(identity_url, data=identity_data, headers=headers)
print("Identity creation response status:", identity_response.status_code)
print("Response URL:", identity_response.url)

if identity_response.status_code == 200:
    # Check if there are form errors
    if 'form-error' in identity_response.text or 'Error' in identity_response.text:
        print("Form validation errors detected")
        # Save response for debugging
        with open('/tmp/identity_error.html', 'w') as f:
            f.write(identity_response.text)
        print("Error response saved to /tmp/identity_error.html")
    else:
        print("Identity creation form processed (may have redirected)")
elif identity_response.status_code == 302:
    print("Identity creation successful - redirected to:", identity_response.url)
    
    # Follow the redirect to see success message
    final_response = client.get(identity_response.url)
    print("Final page status:", final_response.status_code)
    
    if 'success' in final_response.text.lower() or 'created' in final_response.text.lower():
        print("SUCCESS: Identity creation appears successful!")
    else:
        print("Redirected but no clear success message found")
else:
    print("Unexpected status code:", identity_response.status_code)
    print("Response text preview:", identity_response.text[:500])

# Now test that the RFID works by simulating a tap
print("\n--- Testing RFID Tap ---")
hashed_rfid = hashlib.sha256(test_rfid.encode()).hexdigest()
print(f"Hashed RFID: {hashed_rfid}")

tap_data = {
    "device_id": "TEST_READER_01",
    "unit_id": test_unit,
    "hashed_rfid": hashed_rfid,
    "timestamp": str(int(time.time())),
    "direction": "IN"
}
tap_headers = {
    "X-Unit-ID": test_unit
}

tap_response = requests.post('http://localhost:8000/ingest/v2/tap', json=tap_data, headers=tap_headers)
print("Tap ingestion status:", tap_response.status_code)
print("Tap response:", tap_response.text)

# Wait a moment for processing
time.sleep(2)

# Check if attendance record was created
print("\n--- Checking Attendance Record ---")
attendance_check = client.get('http://localhost:8001/edu/api/dashboard-data/')
if attendance_check.status_code == 200:
    data = attendance_check.json()
    print("Dashboard data:", data)
    if data.get('students_present', 0) > 0 or data.get('teachers_on_duty', 0) > 0:
        print("SUCCESS: Tap processed and reflected in dashboard!")
    else:
        print("Tap may not have been processed yet - checking recent taps")
        if data.get('recent_taps'):
            print("Recent taps:", data['recent_taps'])
else:
    print("Failed to get dashboard data:", attendance_check.status_code)

print("\n=== Test Complete ===")