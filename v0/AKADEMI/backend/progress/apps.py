"""Progress App Configuration."""

from django.apps import AppConfig


class ProgressConfig(AppConfig):
    """Progress app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.progress'
    verbose_name = 'Video Progress'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        # Signal'lar
        pass

