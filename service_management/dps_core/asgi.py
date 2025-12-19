import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import student_management.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_management.settings")

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            student_management.routing.websocket_urlpatterns
        )
    ),
})
