# service_management/dps_core/urls.py (Ensure this exists)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Add your student_management app's URLs for API endpoints
    path('api/v1/', include('student_management.urls')),
]