"""
Celery Configuration
====================

Akademi projesi için Celery yapılandırması.
Async task'lar ve periodic task'lar için.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Django settings modülünü ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'akademi.settings')

# Celery uygulamasını oluştur
app = Celery('akademi')

# Django settings'den CELERY_ prefix'li ayarları al
app.config_from_object('django.conf:settings', namespace='CELERY')

# Registered app'lerden task'ları otomatik keşfet
app.autodiscover_tasks()

# =============================================================================
# CELERY BEAT SCHEDULE - Periyodik Görevler
# =============================================================================

app.conf.beat_schedule = {
    # -------------------------------------------------------------------------
    # LIVE SESSION TASKS
    # -------------------------------------------------------------------------
    
    # Süresi dolan kayıtları temizle (her gün 02:00)
    'live-cleanup-expired-recordings': {
        'task': 'backend.live.tasks.cleanup_expired_recordings',
        'schedule': crontab(hour=2, minute=0),
        'options': {'queue': 'live'},
    },
    
    # Heartbeat almayan katılımcıları temizle (her 5 dakika)
    'live-cleanup-stale-participants': {
        'task': 'backend.live.tasks.cleanup_stale_participants',
        'schedule': crontab(minute='*/5'),
        'options': {'queue': 'live'},
    },
    
    # Webhook sağlık kontrolü (her 15 dakika)
    'live-check-webhook-health': {
        'task': 'backend.live.tasks.check_webhook_health',
        'schedule': crontab(minute='*/15'),
        'options': {'queue': 'live'},
    },
    
    # -------------------------------------------------------------------------
    # STORAGE TASKS
    # -------------------------------------------------------------------------
    
    # Süresi dolmuş yükleme oturumlarını temizle (her gün 03:00)
    'storage-cleanup-expired-sessions': {
        'task': 'backend.storage.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=3, minute=0),
        'options': {'queue': 'storage'},
    },
    
    # Silinmiş dosyaları kalıcı olarak kaldır (her gün 04:00)
    'storage-cleanup-deleted-files': {
        'task': 'backend.storage.tasks.cleanup_deleted_files',
        'schedule': crontab(hour=4, minute=0),
        'options': {'queue': 'storage'},
    },
    
    # -------------------------------------------------------------------------
    # CERTIFICATE TASKS
    # -------------------------------------------------------------------------
    
    # Sertifika oluşturma kuyruğunu işle (her 10 dakika)
    # 'certificates-process-queue': {
    #     'task': 'backend.certificates.tasks.process_certificate_queue',
    #     'schedule': crontab(minute='*/10'),
    #     'options': {'queue': 'certificates'},
    # },
    
    # -------------------------------------------------------------------------
    # ANALYTICS TASKS
    # -------------------------------------------------------------------------
    
    # Günlük istatistikleri hesapla (her gün 01:00)
    # 'analytics-daily-stats': {
    #     'task': 'backend.analytics.tasks.calculate_daily_stats',
    #     'schedule': crontab(hour=1, minute=0),
    #     'options': {'queue': 'analytics'},
    # },
}

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # Timezone
    timezone='Europe/Istanbul',
    enable_utc=True,
    
    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend
    result_expires=3600,  # 1 saat
    
    # Rate limits
    task_default_rate_limit='100/m',
    
    # Retry policy
    task_default_retry_delay=60,  # 60 saniye
    task_max_retries=3,
    
    # Queues
    task_default_queue='default',
    task_queues={
        'default': {},
        'live': {'routing_key': 'live.#'},
        'storage': {'routing_key': 'storage.#'},
        'notifications': {'routing_key': 'notifications.#'},
        'certificates': {'routing_key': 'certificates.#'},
        'analytics': {'routing_key': 'analytics.#'},
    },
    
    # Worker
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task - Celery'nin çalıştığını doğrulamak için."""
    print(f'Request: {self.request!r}')

