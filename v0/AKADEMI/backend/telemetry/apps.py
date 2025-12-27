"""Telemetry App Configuration."""

from django.apps import AppConfig


class TelemetryConfig(AppConfig):
    """Telemetry app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.telemetry'
    verbose_name = 'Video Telemetry'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

