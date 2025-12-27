"""
Idempotency Middleware
======================

Global idempotency kontrolü için middleware.
Belirli endpoint'lerde otomatik çalışır.
"""

import json
import logging
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)


class IdempotencyMiddleware:
    """
    Idempotency middleware.
    
    POST/PUT/PATCH isteklerinde Idempotency-Key header'ını kontrol eder.
    Aynı key ile gelen istekleri cache'den döndürür.
    
    Settings:
        IDEMPOTENCY_PATHS: İzlenecek path prefix'leri
        IDEMPOTENCY_TIMEOUT: Cache süresi (default: 3600)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.paths = getattr(settings, 'IDEMPOTENCY_PATHS', [
            '/api/v1/courses/',  # Progress, events, sessions
        ])
        self.timeout = getattr(settings, 'IDEMPOTENCY_TIMEOUT', 3600)
        self.methods = ['POST', 'PUT', 'PATCH']
    
    def __call__(self, request):
        # Sadece belirli method'lar için
        if request.method not in self.methods:
            return self.get_response(request)
        
        # Sadece belirli path'ler için
        if not any(request.path.startswith(p) for p in self.paths):
            return self.get_response(request)
        
        # Idempotency-Key header'ını kontrol et
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return self.get_response(request)
        
        # Cache key oluştur
        user_id = getattr(request.user, 'id', 'anonymous') if hasattr(request, 'user') else 'anonymous'
        cache_key = f"idempotency:{request.path}:{user_id}:{idempotency_key}"
        
        # Cache'de var mı kontrol et
        cached = cache.get(cache_key)
        if cached:
            logger.debug(f"Idempotent replay: {cache_key}")
            response = JsonResponse(
                cached['data'],
                status=cached['status'],
            )
            response['X-Idempotent-Replayed'] = 'true'
            return response
        
        # Normal işlem
        response = self.get_response(request)
        
        # Başarılı response'ları cache'le
        if 200 <= response.status_code < 300:
            try:
                if hasattr(response, 'data'):
                    data = response.data
                elif hasattr(response, 'content'):
                    data = json.loads(response.content.decode())
                else:
                    data = {}
                
                cache.set(
                    cache_key,
                    {
                        'data': data,
                        'status': response.status_code,
                    },
                    timeout=self.timeout
                )
            except Exception as e:
                logger.warning(f"Idempotency cache failed: {e}")
        
        return response

