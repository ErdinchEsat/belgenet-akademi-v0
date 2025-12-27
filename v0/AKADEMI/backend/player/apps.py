"""Player App Configuration."""

from django.apps import AppConfig


class PlayerConfig(AppConfig):
    """Player app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.player'
    verbose_name = 'Video Player'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        # Signal'lar burada import edilir (gerekirse)
        pass

