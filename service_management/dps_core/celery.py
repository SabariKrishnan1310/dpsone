import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dps_core.settings')

# Create the Celery application instance
app = Celery('dps_core')

# Load configuration from the Django settings file, using the 'CELERY' namespace.
# e.g., it looks for settings starting with CELERY_ (like CELERY_BROKER_URL)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed Django apps' 'tasks.py' modules.
app.autodiscover_tasks()