"""Recommendations App Configuration."""

from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    """Recommendations app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.recommendations'
    verbose_name = 'Content Recommendations'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

