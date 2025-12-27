from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.users'
    label = 'users'
    verbose_name = 'Kullanıcılar'

    def ready(self):
        # Signal'leri import et
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

