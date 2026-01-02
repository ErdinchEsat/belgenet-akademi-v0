"""
Cached Model Managers
=====================

Model-level caching için manager'lar.

Kullanım:
--------
from backend.libs.cache.managers import CachedManager

class Course(models.Model):
    objects = CachedManager()
    
# Cache'den al
course = Course.objects.get_cached(pk=1)

# Cache'i invalidate et
Course.objects.invalidate(pk=1)
"""
from typing import Any, Optional, TypeVar, Generic

from django.core.cache import cache
from django.db import models


T = TypeVar('T', bound=models.Model)


class CachedManager(models.Manager, Generic[T]):
    """
    Cache destekli model manager.
    
    Tek kayıtları cache'leyerek tekrarlı DB sorgularını önler.
    
    Attributes:
        cache_timeout: Varsayılan cache süresi (saniye).
        cache_prefix: Cache key prefix.
    """
    cache_timeout: int = 300  # 5 dakika
    cache_prefix: str = 'model'
    
    def _get_cache_key(self, pk: Any) -> str:
        """Model için cache key oluştur."""
        model_label = self.model._meta.label.lower().replace('.', ':')
        return f"akademi:{self.cache_prefix}:{model_label}:{pk}"
    
    def get_cached(self, pk: Any, timeout: Optional[int] = None) -> T:
        """
        Primary key ile cache'den al veya DB'den çek.
        
        Args:
            pk: Primary key değeri.
            timeout: Özel cache süresi (opsiyonel).
        
        Returns:
            Model instance.
        
        Raises:
            DoesNotExist: Kayıt bulunamazsa.
        """
        cache_key = self._get_cache_key(pk)
        instance = cache.get(cache_key)
        
        if instance is None:
            instance = self.get(pk=pk)
            cache.set(cache_key, instance, timeout or self.cache_timeout)
        
        return instance
    
    def get_cached_or_none(self, pk: Any, timeout: Optional[int] = None) -> Optional[T]:
        """
        Primary key ile cache'den al, bulunamazsa None döndür.
        
        Args:
            pk: Primary key değeri.
            timeout: Özel cache süresi (opsiyonel).
        
        Returns:
            Model instance veya None.
        """
        try:
            return self.get_cached(pk, timeout)
        except self.model.DoesNotExist:
            return None
    
    def invalidate(self, pk: Any) -> bool:
        """
        Tek bir kaydın cache'ini temizle.
        
        Args:
            pk: Primary key değeri.
        
        Returns:
            True eğer cache silindiyse.
        """
        cache_key = self._get_cache_key(pk)
        return cache.delete(cache_key)
    
    def invalidate_many(self, pks: list) -> int:
        """
        Birden fazla kaydın cache'ini temizle.
        
        Args:
            pks: Primary key listesi.
        
        Returns:
            Silinen cache sayısı.
        """
        count = 0
        for pk in pks:
            if self.invalidate(pk):
                count += 1
        return count
    
    def set_cached(self, instance: T, timeout: Optional[int] = None) -> None:
        """
        Model instance'ı cache'e kaydet.
        
        Args:
            instance: Model instance.
            timeout: Özel cache süresi (opsiyonel).
        """
        cache_key = self._get_cache_key(instance.pk)
        cache.set(cache_key, instance, timeout or self.cache_timeout)


class TenantCachedManager(CachedManager[T]):
    """
    Tenant-aware cached manager.
    
    Cache key'lere tenant ID ekler.
    """
    
    def _get_cache_key(self, pk: Any, tenant_id: Optional[Any] = None) -> str:
        """Tenant-aware cache key oluştur."""
        model_label = self.model._meta.label.lower().replace('.', ':')
        base_key = f"akademi:{self.cache_prefix}:{model_label}"
        
        if tenant_id:
            return f"{base_key}:t{tenant_id}:{pk}"
        return f"{base_key}:{pk}"
    
    def get_cached_for_tenant(
        self, 
        pk: Any, 
        tenant_id: Any, 
        timeout: Optional[int] = None
    ) -> T:
        """
        Tenant bazlı cache'den al.
        
        Args:
            pk: Primary key değeri.
            tenant_id: Tenant ID.
            timeout: Özel cache süresi (opsiyonel).
        
        Returns:
            Model instance.
        """
        cache_key = self._get_cache_key(pk, tenant_id)
        instance = cache.get(cache_key)
        
        if instance is None:
            instance = self.get(pk=pk)
            cache.set(cache_key, instance, timeout or self.cache_timeout)
        
        return instance
    
    def invalidate_for_tenant(self, pk: Any, tenant_id: Any) -> bool:
        """Tenant bazlı cache temizle."""
        cache_key = self._get_cache_key(pk, tenant_id)
        return cache.delete(cache_key)
