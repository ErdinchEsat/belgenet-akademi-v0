"""Realtime App Configuration."""

from django.apps import AppConfig


class RealtimeConfig(AppConfig):
    """Realtime uygulama yapılandırması."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.realtime'
    verbose_name = 'Gerçek Zamanlı İletişim'
    
    def ready(self):
        """Uygulama hazır olduğunda çalışır."""
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

