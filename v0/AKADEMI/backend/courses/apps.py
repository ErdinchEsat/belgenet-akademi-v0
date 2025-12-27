from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.courses'
    label = 'courses'
    verbose_name = 'Kurslar'

    def ready(self):
        try:
            from . import signals  # noqa: F401
        except ImportError:
            pass

