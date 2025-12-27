"""
Live Class Providers
====================

Provider-agnostic canlı ders sağlayıcı modülü.
Jitsi, BBB ve Zoom adapter'larını içerir.
"""

from typing import TYPE_CHECKING

from .base import LiveClassProvider, RoomInfo, JoinInfo, ParticipantInfo, RecordingInfo, NormalizedEvent
from .jitsi import JitsiProvider

if TYPE_CHECKING:
    from backend.tenants.models import Tenant
    from backend.live.models import LiveProviderConfig


def get_provider(tenant: 'Tenant') -> LiveClassProvider:
    """
    Tenant için aktif provider'ı döner.
    
    Args:
        tenant: Provider alınacak tenant
        
    Returns:
        LiveClassProvider: Aktif provider instance
        
    Raises:
        ValueError: Aktif provider bulunamazsa
    """
    from backend.live.models import LiveProviderConfig
    
    config = LiveProviderConfig.objects.filter(
        tenant=tenant,
        is_active=True,
        is_default=True,
    ).first()
    
    if not config:
        # Fallback: Aktif herhangi bir config
        config = LiveProviderConfig.objects.filter(
            tenant=tenant,
            is_active=True,
        ).first()
    
    if not config:
        raise ValueError(f"No active live provider for tenant: {tenant.slug}")
    
    return get_provider_for_config(config)


def get_provider_for_config(config: 'LiveProviderConfig') -> LiveClassProvider:
    """
    Config için provider instance döner.
    
    Args:
        config: Provider konfigürasyonu
        
    Returns:
        LiveClassProvider: Provider instance
        
    Raises:
        ValueError: Bilinmeyen provider türü
    """
    from .jitsi import JitsiProvider
    from .bbb import BBBProvider
    from .zoom import ZoomProvider
    
    if config.provider == 'jitsi':
        return JitsiProvider(config)
    elif config.provider == 'bbb':
        return BBBProvider(config)
    elif config.provider == 'zoom':
        return ZoomProvider(config)
    
    raise ValueError(f"Unknown provider: {config.provider}")


__all__ = [
    'LiveClassProvider',
    'RoomInfo',
    'JoinInfo',
    'ParticipantInfo',
    'RecordingInfo',
    'NormalizedEvent',
    'JitsiProvider',
    'get_provider',
    'get_provider_for_config',
]

