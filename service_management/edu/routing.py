from django.urls import path
from .consumers import SchoolConsumer

websocket_urlpatterns = [
    path('ws/edu/dashboard/', SchoolConsumer.as_asgi()),
]