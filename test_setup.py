import os
import sys
import django
import hashlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base_core.settings')
sys.path.append('/usr/src/app')
django.setup()

from sterling_core.models import Unit, SterlingUser, Organization
from edu.models import EduProfile
from django.core.cache import cache

# Create org and unit
org, _ = Organization.objects.get_or_create(name='DPS')
unit, _ = Unit.objects.get_or_create(name='Main Campus', organization=org)

# Create user with RFID
raw_rfid = 'TEST_RFID_123'
hashed = hashlib.sha256(raw_rfid.encode()).hexdigest()

user, _ = SterlingUser.objects.get_or_create(
    username='test_student',
    defaults={'email': 'student@example.com'}
)
user.set_password('1234')
user.hashed_rfid = hashed
user.save()

# Create EduProfile
EduProfile.objects.get_or_create(user=user, defaults={'role_type': 'STUDENT'})

# Warm up Redis
from sterling_core.signals import get_redis_client
r = get_redis_client()
r.hset(f"cache:rfid:{hashed}", mapping={
    "user_id": str(user.id),
    "primary_unit_id": str(unit.id)
})
r.hset(f"cache:unit:{unit.id}", mapping={
    "vertical": "SCHOOL"
})

print(f"Setup complete. Hashed RFID: {hashed}")
print(f"User ID: {user.id}")
print(f"Unit ID: {unit.id}")
