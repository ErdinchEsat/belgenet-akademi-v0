# B6 - Canlı Ders Modülü (Live Session)

Akademi LMS için canlı ders (video konferans) modülü. Provider-agnostic mimari ile Jitsi, BigBlueButton ve Zoom destekler.

## Özellikler

- 🎥 **Canlı Ders Yönetimi**: Planlı dersler, anlık toplantılar, webinar
- 👥 **Katılım Takibi**: Otomatik yoklama, heartbeat, attendance raporu
- 📹 **Kayıt Yönetimi**: Otomatik/manuel kayıt, storage entegrasyonu
- 🔐 **JWT Tabanlı Auth**: Güvenli katılım token'ları
- 📅 **Takvim Entegrasyonu**: ICS dosyası, hatırlatıcılar
- 📊 **Raporlar**: Yoklama CSV export, katılım analizi

## Kurulum

### 1. Requirements

```bash
pip install -r tools/requirements/live.txt
```

### 2. Migration

```bash
cd v0/AKADEMI
python manage.py makemigrations live
python manage.py migrate
```

### 3. Environment Variables

`.env` dosyasına ekleyin:

```bash
# Jitsi
JITSI_DOMAIN=meet.yourdomain.com
JITSI_APP_ID=edutech
JITSI_JWT_SECRET=your-secret-key-min-32-chars

# BBB (opsiyonel)
BBB_SERVER_URL=https://bbb.yourdomain.com/bigbluebutton
BBB_SHARED_SECRET=your-bbb-secret
```

### 4. Jitsi Docker (Self-hosted)

```bash
cd v0/MAYSCON/mayscon.v1/infra/docker
docker-compose -f docker-compose.jitsi.yml up -d
```

### 5. Celery Worker

```bash
# Worker
celery -A akademi worker -l info -Q default,live,notifications

# Beat (periodic tasks)
celery -A akademi beat -l info
```

## API Endpoints

### Session Management

```
POST   /api/v1/live-sessions/sessions/           # Yeni ders oluştur
GET    /api/v1/live-sessions/sessions/           # Liste
GET    /api/v1/live-sessions/sessions/{id}/      # Detay
PUT    /api/v1/live-sessions/sessions/{id}/      # Güncelle
DELETE /api/v1/live-sessions/sessions/{id}/      # Sil
```

### Session Actions

```
POST   /api/v1/live-sessions/sessions/{id}/start/     # Başlat
POST   /api/v1/live-sessions/sessions/{id}/join/      # Katıl (JWT token al)
POST   /api/v1/live-sessions/sessions/{id}/end/       # Bitir
POST   /api/v1/live-sessions/sessions/{id}/cancel/    # İptal et
POST   /api/v1/live-sessions/sessions/{id}/heartbeat/ # Heartbeat
```

### Reports & Media

```
GET    /api/v1/live-sessions/sessions/{id}/attendance/    # Yoklama
GET    /api/v1/live-sessions/sessions/{id}/participants/  # Katılımcılar
GET    /api/v1/live-sessions/sessions/{id}/recordings/    # Kayıtlar
GET    /api/v1/live-sessions/sessions/{id}/artifacts/     # Çıktılar
GET    /api/v1/live-sessions/sessions/{id}/calendar/      # ICS dosyası
```

### Webhooks

```
POST   /api/v1/live-sessions/webhooks/jitsi/   # Jitsi webhook
POST   /api/v1/live-sessions/webhooks/bbb/     # BBB webhook
```

## Provider Konfigürasyonu

### Admin Panelden

1. Django Admin > Live Provider Configs
2. Tenant seçin
3. Provider ayarlarını girin
4. "Is Default" işaretleyin

### Programatik

```python
from backend.live.models import LiveProviderConfig

LiveProviderConfig.objects.create(
    tenant=tenant,
    provider='jitsi',
    is_active=True,
    is_default=True,
    jitsi_domain='meet.yourdomain.com',
    jitsi_app_id='edutech',
    jitsi_jwt_secret='your-secret-key',
)
```

## Kullanım Örneği

### Session Oluşturma

```python
from backend.live.services.session_service import LiveSessionService
from datetime import timedelta
from django.utils import timezone

session = LiveSessionService.create_session(
    tenant=tenant,
    course=course,
    title="Hafta 1 - Giriş Dersi",
    scheduled_start=timezone.now() + timedelta(hours=1),
    scheduled_end=timezone.now() + timedelta(hours=2),
    created_by=instructor,
    recording_enabled=True,
)
```

### Join URL Alma

```python
from backend.live.providers import get_provider

provider = get_provider(tenant)
join_info = provider.generate_join_url(session, user, role='participant')

print(join_info.join_url)  # https://meet.domain.com/room?jwt=...
```

## Dosya Yapısı

```
backend/live/
├── models.py           # 7 model
├── serializers.py      # API serializers
├── views.py            # ViewSets
├── urls.py             # URL routing
├── permissions.py      # Permission classes
├── tasks.py            # Celery tasks
├── admin.py            # Django admin
├── signals.py          # Audit logging
├── providers/
│   ├── base.py         # Abstract interface
│   ├── jitsi.py        # Jitsi adapter
│   ├── bbb.py          # BBB adapter
│   └── zoom.py         # Zoom placeholder
├── services/
│   ├── session_service.py
│   ├── attendance_service.py
│   ├── recording_service.py
│   ├── webhook_service.py
│   └── calendar_service.py
└── tests/
    ├── test_models.py
    └── test_providers.py
```

## Webhook Konfigürasyonu

### Jitsi (Prosody)

Prosody modülü ile webhook göndermek için:

```lua
-- /etc/prosody/conf.d/webhook.cfg.lua
VirtualHost "meet.yourdomain.com"
    modules_enabled = { "webhook" }
    webhook_url = "https://api.yourdomain.com/api/v1/live-sessions/webhooks/jitsi/"
```

### BBB

BBB webhooks modülü ile:

```bash
bbb-conf --setip https://api.yourdomain.com/api/v1/live-sessions/webhooks/bbb/
```

## Monitoring

### Health Check

```
GET /api/v1/live-sessions/ops/
```

### Prometheus Metrics (TODO)

```
live_sessions_active_total
live_participants_total
live_webhook_events_total
live_recording_processing_seconds
```

## Lisans

Proprietary - EduTech/Akademi İstanbul

