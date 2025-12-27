"""Integrity App Configuration."""

from django.apps import AppConfig


class IntegrityConfig(AppConfig):
    """Integrity app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.integrity'
    verbose_name = 'Playback Integrity'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

