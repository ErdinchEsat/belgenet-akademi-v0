"""Certificates App Configuration."""

from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    """Sertifika uygulama yapılandırması."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.certificates'
    verbose_name = 'Sertifikalar'
    
    def ready(self):
        """Uygulama hazır olduğunda çalışır."""
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

