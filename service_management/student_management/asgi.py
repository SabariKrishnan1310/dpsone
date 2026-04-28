import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
import student_management.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sterlingone_core.settings")
django.setup()

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            student_management.routing.websocket_urlpatterns
        )
    ),
})
