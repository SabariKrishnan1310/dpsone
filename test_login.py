import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'base_core.settings')
sys.path.append('/usr/src/app')
django.setup()

from django.test import Client
from django.urls import reverse

c = Client()
# Get login page to get CSRF token
resp = c.get('/edu/login/')
print('Login page status:', resp.status_code)
# For simplicity, we'll just post with the credentials (Django test client handles CSRF)
login_data = {'username': 'sabari', 'password': '1234'}
resp = c.post('/edu/login/', login_data)
print('Login response status:', resp.status_code)
print('Login response redirect_chain:', resp.redirect_chain)
# Follow redirect to dashboard
if resp.status_code == 302:
    resp = c.get(resp['Location'])
    print('Dashboard status:', resp.status_code)
    # Check if dashboard contains expected text
    content = resp.content.decode('utf-8')
    if 'SterlingONE' in content:
        print('Dashboard contains SterlingONE - SUCCESS')
    else:
        print('Dashboard does not contain SterlingONE')
        print('Content preview:', content[:200])
else:
    print('Login failed, not redirected')
    print('Response content:', resp.content.decode('utf-8')[:500])