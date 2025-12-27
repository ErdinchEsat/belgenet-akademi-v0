"""Timeline App Configuration."""

from django.apps import AppConfig


class TimelineConfig(AppConfig):
    """Timeline app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.timeline'
    verbose_name = 'Interactive Timeline'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

