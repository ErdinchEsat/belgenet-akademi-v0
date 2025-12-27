"""
Idempotency Decorators
======================

View ve ViewSet method'ları için idempotency decorator'ları.
"""

import hashlib
import json
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response


def idempotent(timeout=3600, key_prefix='idempotent'):
    """
    Idempotent endpoint decorator.
    
    Aynı Idempotency-Key ile gelen istekleri cache'den döndürür.
    
    Kullanım:
        @idempotent(timeout=3600)
        def create(self, request, *args, **kwargs):
            ...
    
    Args:
        timeout: Cache süresi (saniye), default 1 saat
        key_prefix: Cache key prefix'i
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Idempotency-Key header'ını kontrol et
            idempotency_key = request.headers.get('Idempotency-Key')
            
            if not idempotency_key:
                # Key yoksa normal işlem
                return func(self, request, *args, **kwargs)
            
            # Cache key oluştur
            user_id = getattr(request.user, 'id', 'anonymous')
            cache_key = f"{key_prefix}:{user_id}:{idempotency_key}"
            
            # Cache'de var mı kontrol et
            cached_response = cache.get(cache_key)
            if cached_response:
                return Response(
                    data=cached_response['data'],
                    status=cached_response['status'],
                    headers={'X-Idempotent-Replayed': 'true'}
                )
            
            # İşlemi gerçekleştir
            response = func(self, request, *args, **kwargs)
            
            # Başarılı response'ları cache'le
            if 200 <= response.status_code < 300:
                cache.set(
                    cache_key,
                    {
                        'data': response.data,
                        'status': response.status_code,
                    },
                    timeout=timeout
                )
            
            return response
        return wrapper
    return decorator


def generate_idempotency_key(data: dict) -> str:
    """
    Request data'dan idempotency key üret.
    
    Client tarafında kullanılabilir.
    """
    json_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()[:32]

