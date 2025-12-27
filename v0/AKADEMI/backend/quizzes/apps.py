"""Quizzes App Configuration."""

from django.apps import AppConfig


class QuizzesConfig(AppConfig):
    """Quizzes app configuration."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend.quizzes'
    verbose_name = 'Quizzes'
    
    def ready(self):
        """App başlatıldığında çalışır."""
        pass

