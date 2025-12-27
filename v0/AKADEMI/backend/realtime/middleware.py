"""
WebSocket Authentication Middleware
====================================

JWT token ile WebSocket bağlantı doğrulama.
"""

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token):
    """
    JWT token'dan kullanıcı döndürür.
    """
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        # Token'ı decode et
        access_token = AccessToken(token)
        user_id = access_token.get('user_id')
        
        if not user_id:
            return AnonymousUser()
        
        # Kullanıcıyı getir
        user = User.objects.select_related('tenant').get(id=user_id)
        return user
        
    except Exception as e:
        logger.debug(f"Token doğrulama hatası: {e}")
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    JWT Authentication Middleware for WebSocket.
    
    Token query parameter veya header üzerinden alınır:
    - ws://example.com/ws/notifications/?token=<JWT>
    - Authorization: Bearer <JWT>
    """
    
    async def __call__(self, scope, receive, send):
        # Query string'den token al
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        
        token = None
        
        # Query parameter'dan token
        if 'token' in query_params:
            token = query_params['token'][0]
        
        # Header'dan token (subprotocol olarak)
        if not token:
            headers = dict(scope.get('headers', []))
            auth_header = headers.get(b'authorization', b'').decode()
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
        
        # Subprotocols'dan token (WebSocket handshake)
        if not token:
            subprotocols = scope.get('subprotocols', [])
            for subprotocol in subprotocols:
                if subprotocol.startswith('token.'):
                    token = subprotocol[6:]
                    break
        
        # Token varsa kullanıcıyı doğrula
        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
        
        return await super().__call__(scope, receive, send)


class TenantMiddleware(BaseMiddleware):
    """
    Tenant bilgisini scope'a ekler.
    """
    
    async def __call__(self, scope, receive, send):
        user = scope.get('user')
        
        if user and hasattr(user, 'tenant'):
            scope['tenant'] = user.tenant
            scope['tenant_id'] = user.tenant_id
        else:
            scope['tenant'] = None
            scope['tenant_id'] = None
        
        return await super().__call__(scope, receive, send)

