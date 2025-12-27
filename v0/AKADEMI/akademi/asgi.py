"""
ASGI config for akademi project.

Django Channels ile WebSocket desteği sağlar.

Routing:
- HTTP istekleri → Django ASGI application
- WebSocket istekleri → Channels consumers

WebSocket Endpoints:
- /ws/notifications/ - Gerçek zamanlı bildirimler
- /ws/messages/ - Gerçek zamanlı mesajlaşma
- /ws/messages/{conversation_id}/ - Konuşma odası

Kullanım:
--------
# Development
daphne akademi.asgi:application

# Production (gunicorn + uvicorn workers)
gunicorn akademi.asgi:application -k uvicorn.workers.UvicornWorker
"""

import os
import sys
from pathlib import Path

# MAYSCON.V1 PATH CONFIGURATION
BASE_DIR = Path(__file__).resolve().parent.parent
MAYSCON_V1_PATH = BASE_DIR.parent / 'MAYSCON' / 'mayscon.v1'

if str(MAYSCON_V1_PATH) not in sys.path:
    sys.path.insert(0, str(MAYSCON_V1_PATH))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "akademi.settings")

# Django ASGI application'ı önce yükle
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Channels routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

# Auth middleware import (channels kurulu olduğunda)
try:
    from channels.auth import AuthMiddlewareStack
    from backend.realtime.middleware import JWTAuthMiddleware
    from backend.realtime.routing import websocket_urlpatterns
    
    application = ProtocolTypeRouter({
        # HTTP → Django
        "http": django_asgi_app,
        
        # WebSocket → Channels
        "websocket": AllowedHostsOriginValidator(
            JWTAuthMiddleware(
                URLRouter(websocket_urlpatterns)
            )
        ),
    })
    
except ImportError:
    # Channels yüklü değilse sadece HTTP
    application = django_asgi_app
