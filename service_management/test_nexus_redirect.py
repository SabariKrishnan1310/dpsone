import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base_core.settings')
# The directory is /usr/src/app in the container
sys.path.append('/usr/src/app')
django.setup()

from django.test import Client
from django.urls import reverse
from sterling_core.models import SterlingUser

c = Client()
# Test Superuser sabari
print('--- Testing Superuser ---')
user = SterlingUser.objects.get(username='sabari')
c.force_login(user)
resp = c.get('/')
print('Redirect from /:', resp.status_code, resp.url if hasattr(resp, 'url') else '')
if resp.url == reverse('nexus:dashboard'):
    print('SUCCESS: Redirected to Nexus')
else:
    print('FAILED: Not redirected to Nexus')

# Need to create a principal
print('\n--- Testing Principal ---')
# First, create a unit and org
from sterling_core.models import Organization, Unit
from sterling_core.models import Membership
org = Organization.objects.create(name='EuroKids Chain', slug='eurokids')
unit = Unit.objects.create(name='EuroKids Bengaluru', unit_code='EKB', organization=org)
principal = SterlingUser.objects.create_user(username='principal1', password='password')
Membership.objects.create(user=principal, unit=unit, role='MANAGER', is_primary=True)

c.force_login(principal)
resp = c.get('/')
print('Redirect from /:', resp.status_code, resp.url if hasattr(resp, 'url') else '')
if resp.url == reverse('edu:dashboard'):
    print('SUCCESS: Redirected to Edu Dashboard')
else:
    print('FAILED: Not redirected to Edu Dashboard')

# Check security
resp = c.get('/nexus/dashboard/')
print('Access /nexus/dashboard/:', resp.status_code)
if resp.status_code == 403:
    print('SUCCESS: Principal forbidden from /nexus/')
else:
    print('FAILED: Principal not forbidden')
