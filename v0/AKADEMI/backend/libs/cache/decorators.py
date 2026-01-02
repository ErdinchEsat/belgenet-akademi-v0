"""
Cache Decorators
================

API view'ları için tenant-aware caching decorators.

Kullanım:
--------
from backend.libs.cache.decorators import cache_per_tenant, cache_response

class CourseViewSet(viewsets.ModelViewSet):
    @cache_per_tenant(timeout=60, key_prefix='courses')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
"""
import hashlib
from functools import wraps
from typing import List, Optional, Callable

from django.core.cache import cache
from django.conf import settings
from rest_framework.response import Response


def make_cache_key(
    prefix: str,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    path: str = '',
    query_string: str = ''
) -> str:
    """
    Cache key oluştur.
    
    Format: {prefix}:{tenant_id}:{user_id}:{path_hash}
    """
    parts = ['akademi', prefix]
    
    if tenant_id:
        parts.append(f't{tenant_id}')
    
    if user_id:
        parts.append(f'u{user_id}')
    
    # Path ve query string hash'le
    if path or query_string:
        path_data = f"{path}?{query_string}" if query_string else path
        path_hash = hashlib.md5(path_data.encode()).hexdigest()[:12]
        parts.append(path_hash)
    
    return ':'.join(parts)


def cache_per_tenant(timeout: int = 300, key_prefix: str = 'view'):
    """
    Tenant bazlı cache decorator.
    
    Her tenant ve kullanıcı için ayrı cache key oluşturur.
    
    Args:
        timeout: Cache TTL (saniye). Varsayılan 5 dakika.
        key_prefix: Cache key prefix.
    
    Usage:
        @cache_per_tenant(timeout=60, key_prefix='courses')
        def list(self, request, *args, **kwargs):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # DEBUG modda cache devre dışı
            if getattr(settings, 'DEBUG', False) and not getattr(settings, 'ENABLE_CACHE_IN_DEBUG', False):
                return view_func(self, request, *args, **kwargs)
            
            # Cache key oluştur
            tenant_id = getattr(request.user, 'tenant_id', None)
            user_id = getattr(request.user, 'id', None)
            query_string = request.META.get('QUERY_STRING', '')
            
            cache_key = make_cache_key(
                prefix=key_prefix,
                tenant_id=str(tenant_id) if tenant_id else None,
                user_id=str(user_id) if user_id else None,
                path=request.path,
                query_string=query_string
            )
            
            # Cache'den al
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)
            
            # View'ı çalıştır
            response = view_func(self, request, *args, **kwargs)
            
            # Başarılı response'u cache'le
            if response.status_code == 200:
                # Response data'yı cache'le (Response objesi değil)
                cache.set(cache_key, response.data, timeout)
            
            return response
        return wrapper
    return decorator


def cache_response(timeout: int = 300, key_func: Optional[Callable] = None):
    """
    Basit response caching decorator.
    
    Custom key function ile kullanılabilir.
    
    Args:
        timeout: Cache TTL (saniye).
        key_func: Custom cache key oluşturucu. (request) -> str
    
    Usage:
        @cache_response(timeout=60, key_func=lambda r: f"user:{r.user.id}")
        def get(self, request):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Cache key
            if key_func:
                cache_key = f"akademi:response:{key_func(request)}"
            else:
                cache_key = make_cache_key(
                    prefix='response',
                    path=request.path,
                    query_string=request.META.get('QUERY_STRING', '')
                )
            
            # Cache'den al
            cached_data = cache.get(cache_key)
            if cached_data is not None:
                return Response(cached_data)
            
            # View'ı çalıştır
            response = view_func(self, request, *args, **kwargs)
            
            if response.status_code == 200:
                cache.set(cache_key, response.data, timeout)
            
            return response
        return wrapper
    return decorator


def invalidate_cache_patterns(patterns: List[str]):
    """
    Pattern bazlı cache invalidation decorator.
    
    POST/PUT/DELETE işlemlerinden sonra ilgili cache'leri temizler.
    
    Args:
        patterns: Invalidate edilecek key pattern'ları.
    
    Usage:
        @invalidate_cache_patterns(['courses:*', 'enrollments:*'])
        def create(self, request, *args, **kwargs):
            ...
    """
    def decorator(view_func: Callable):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            result = view_func(self, request, *args, **kwargs)
            
            # Başarılı mutasyon sonrası cache'i temizle
            if result.status_code in [200, 201, 204]:
                for pattern in patterns:
                    try:
                        # django-redis delete_pattern kullan
                        cache.delete_pattern(f"akademi:{pattern}")
                    except AttributeError:
                        # LocMemCache için pattern delete yok, skip
                        pass
            
            return result
        return wrapper
    return decorator
