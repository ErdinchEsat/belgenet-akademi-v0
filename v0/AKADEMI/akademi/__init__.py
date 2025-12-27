"""
Akademi Django Projesi
======================

EduTech/Akademi İstanbul LMS.
"""

# Celery app'i Django başladığında yükle
# Bu satır, Celery'nin shared_task decorator'ını kullanabilmesi için gerekli
from .celery import app as celery_app

__all__ = ('celery_app',)

