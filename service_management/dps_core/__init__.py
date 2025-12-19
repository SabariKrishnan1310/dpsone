# service_management/dps_core/__init__.py

# This ensures the Celery app is loaded when Django starts
from .celery import app as celery_app 

# Optional: define your default Django app setup here