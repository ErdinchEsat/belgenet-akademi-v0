"""
Live Session URLs
=================

Canlı ders API endpoint URL tanımlamaları.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    LiveSessionViewSet,
    RecordingViewSet,
    WebhookView,
    LiveProviderConfigView,
    LiveOpsView,
)

app_name = 'live'

router = DefaultRouter()
router.register('sessions', LiveSessionViewSet, basename='session')
router.register('recordings', RecordingViewSet, basename='recording')

urlpatterns = [
    # ViewSet routes
    path('', include(router.urls)),
    
    # Webhook handlers
    path('webhooks/<str:provider>/', WebhookView.as_view(), name='webhook'),
    
    # Provider config (Tenant admin)
    # Not: Bu URL genellikle /api/v1/tenants/{id}/live-config/ olarak kullanılır
    # Buraya alternatif olarak ekliyoruz
    path('config/', LiveProviderConfigView.as_view(), {'tenant_id': None}, name='config'),
    
    # Live ops dashboard
    path('ops/', LiveOpsView.as_view(), name='ops'),
]

# URL yapısı:
# 
# /api/v1/live-sessions/sessions/                    - Liste
# /api/v1/live-sessions/sessions/{id}/               - Detay
# /api/v1/live-sessions/sessions/{id}/start/         - Başlat
# /api/v1/live-sessions/sessions/{id}/join/          - Katıl
# /api/v1/live-sessions/sessions/{id}/end/           - Bitir
# /api/v1/live-sessions/sessions/{id}/cancel/        - İptal
# /api/v1/live-sessions/sessions/{id}/heartbeat/     - Heartbeat
# /api/v1/live-sessions/sessions/{id}/attendance/    - Yoklama
# /api/v1/live-sessions/sessions/{id}/participants/  - Katılımcılar
# /api/v1/live-sessions/sessions/{id}/recordings/    - Kayıtlar
# /api/v1/live-sessions/sessions/{id}/artifacts/     - Çıktılar
# /api/v1/live-sessions/sessions/{id}/calendar/      - ICS
#
# /api/v1/live-sessions/recordings/                  - Kayıt listesi
# /api/v1/live-sessions/recordings/{id}/publish/     - Yayınla
# /api/v1/live-sessions/recordings/{id}/unpublish/   - Yayından kaldır
#
# /api/v1/live-sessions/webhooks/jitsi/              - Jitsi webhook
# /api/v1/live-sessions/webhooks/bbb/                - BBB webhook
#
# /api/v1/live-sessions/ops/                         - Admin ops dashboard

