"""Storage App Configuration."""

from django.apps import AppConfig


class StorageConfig(AppConfig):
    """Storage uygulama yapılandırması."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.storage'
    verbose_name = 'Dosya Depolama'
    
    def ready(self):
        """Uygulama hazır olduğunda çalışır."""
        # Signal'ları import et
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

