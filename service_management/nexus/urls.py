from django.urls import path
from . import views

app_name = "nexus"

urlpatterns = [
    path("dashboard/", views.nexus_dashboard, name="dashboard"),
]
