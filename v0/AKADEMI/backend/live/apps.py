"""
Live App Configuration
"""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class LiveConfig(AppConfig):
    """Canlı Ders modülü konfigürasyonu."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.live'
    verbose_name = _('Canlı Dersler')
    
    def ready(self):
        """App hazır olduğunda çalışır."""
        # Signal'ları import et
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

