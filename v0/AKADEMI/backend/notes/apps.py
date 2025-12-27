"""Notes App Configuration."""

from django.apps import AppConfig


class NotesConfig(AppConfig):
    """Notes app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.notes'
    verbose_name = 'Video Notes'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

