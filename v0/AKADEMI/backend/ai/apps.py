"""AI App Configuration."""

from django.apps import AppConfig


class AIConfig(AppConfig):
    """AI app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.ai'
    verbose_name = 'AI Features'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

