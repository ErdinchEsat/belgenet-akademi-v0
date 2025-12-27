"""Sequencing App Configuration."""

from django.apps import AppConfig


class SequencingConfig(AppConfig):
    """Sequencing app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.sequencing'
    verbose_name = 'Content Sequencing'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        # Signal'lar burada import edilir
        pass

