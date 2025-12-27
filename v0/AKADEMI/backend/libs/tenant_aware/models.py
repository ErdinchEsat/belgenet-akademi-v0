"""
Tenant Aware Base Models
========================

Tüm tenant-scoped modeller bu base class'ları kullanır.
Otomatik tenant filtreleme ve isolation sağlar.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class TenantAwareManager(models.Manager):
    """
    Tenant-aware queryset manager.
    
    Otomatik olarak tenant filtrelemesi yapar.
    Kullanım:
        # View'da tenant'ı set et
        MyModel.objects.for_tenant(request.user.tenant)
    """
    
    def for_tenant(self, tenant):
        """Belirli bir tenant için queryset döndür."""
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)
    
    def for_tenant_id(self, tenant_id):
        """Tenant ID ile queryset döndür."""
        if tenant_id is None:
            return self.none()
        return self.filter(tenant_id=tenant_id)


class TenantAwareModel(models.Model):
    """
    Multi-tenant model base class.
    
    Tüm tenant-scoped modeller bu class'tan türetilmeli.
    Otomatik olarak tenant FK ve UUID primary key ekler.
    
    Örnek:
        class PlaybackSession(TenantAwareModel):
            user = models.ForeignKey(...)
            # tenant otomatik eklenir
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss',  # Örn: playbacksessions, telemetryevents
        verbose_name=_('Tenant'),
        db_index=True,
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Oluşturulma'),
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Güncellenme'),
    )
    
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        """Tenant kontrolü ile kaydet."""
        if not self.tenant_id:
            raise ValueError("Tenant is required for TenantAwareModel")
        super().save(*args, **kwargs)


class TenantAwareModelNoTimestamps(models.Model):
    """
    Timestamp'siz tenant-aware model.
    
    Append-only tablolar için (örn: TelemetryEvent).
    updated_at gereksiz olduğunda kullanılır.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name=_('ID'),
    )
    
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name=_('Tenant'),
        db_index=True,
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Oluşturulma'),
        db_index=True,
    )
    
    objects = TenantAwareManager()
    
    class Meta:
        abstract = True
        ordering = ['-created_at']

