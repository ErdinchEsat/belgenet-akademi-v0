# Backend Unit Test - Kurulum ve Çalıştırma Kılavuzu

> **Tarih:** 29 Aralık 2024
> **Durum:** Test altyapısı hazır, Docker ortamında çalıştırılması gerekiyor

---

## 📋 Özet

Bu proje **Docker** ortamında çalışacak şekilde yapılandırılmıştır. Local ortamda PostgreSQL, Redis ve diğer servisler olmadan testler çalışmaz.

---

## 🏗️ Mimari: Merkezi Ayar Sistemi

**Akademi projesi, MAYSCON'un merkezi ayar sistemini kullanıyor:**

```
v0/AKADEMI/akademi/settings.py
    └── from config.settings import *  # MAYSCON'dan kalıtım
        │
        ├── v0/MAYSCON/mayscon.v1/config/settings/
        │   ├── base.py          # Temel ayarlar
        │   ├── apps.py          # INSTALLED_APPS
        │   ├── middleware.py    # MIDDLEWARE
        │   ├── auth.py          # Authentication
        │   ├── data/            # Database (PostgreSQL)
        │   ├── cache.py         # Redis cache
        │   └── logging/         # Logging yapılandırması
        │
        └── v0/MAYSCON/mayscon.v1/tools/requirements/
            ├── base.txt         # Temel bağımlılıklar
            ├── api.txt          # REST API
            ├── data.txt         # PostgreSQL, Redis, Celery
            ├── dev.txt          # Test & Development
            └── storage.txt      # S3, Pillow, PDF
```

Bu yapı sayesinde:
- Tüm bağımlılıklar MAYSCON'da tanımlı
- Akademi sadece override'lar ekliyor
- Test ayarları da aynı yapıyı kullanıyor

---

## ✅ Tamamlanan İşler

### 1. Bağımlılıklar Güncellendi

**Dosya:** `v0/MAYSCON/mayscon.v1/tools/requirements/base.txt`
```
python-slugify>=8.0.0         # URL-friendly slug oluşturma
hashids>=1.3.0                # ID encoding/decoding
Pillow>=10.2.0                # Image işleme
```

**Dosya:** `v0/MAYSCON/mayscon.v1/tools/requirements/dev.txt`
```
pytest-timeout>=2.3.0         # Test timeout
pytest-mock>=3.12.0           # Mock helpers
freezegun>=1.4.0              # Time mocking
responses>=0.25.0             # HTTP mocking
requests-mock>=1.11.0         # Requests mocking
```

### 2. Test Settings Dosyası Oluşturuldu
**Dosya:** `v0/AKADEMI/akademi/settings_test.py`

```python
# Test ortamı için özelleştirilmiş ayarlar
- DEBUG = False
- SQLite in-memory database (Docker'da PostgreSQL kullanılacak)
- Debug toolbar ve monitor middleware devre dışı
- Celery eager mode
- Minimal logging
- Hızlı password hasher
```

### 3. pytest.ini Güncellendi
**Dosya:** `v0/MAYSCON/mayscon.v1/tests/akademi/pytest.ini`

```ini
DJANGO_SETTINGS_MODULE = akademi.settings_test
```

### 4. conftest.py Güncellendi
**Dosya:** `v0/MAYSCON/mayscon.v1/tests/akademi/conftest.py`

- Path konfigürasyonu düzeltildi (AKADEMI_PATH = parents[4])
- pytest_configure() sadeleştirildi
- Test settings modülünü kullanacak şekilde ayarlandı

### 5. Virtual Environment Oluşturuldu (Local Test İçin)
**Konum:** `v0/MAYSCON/mayscon.v1/venv/`

Kurulu paketler:
- pytest, pytest-django, pytest-cov, pytest-xdist, pytest-timeout
- factory-boy, faker, freezegun, responses
- Django 5.2.9, djangorestframework, djangorestframework-simplejwt
- celery, redis, channels, pillow, boto3
- Ve diğer proje bağımlılıkları

---

## 🐳 Docker Test Ortamı

### Mevcut Sürümler (Projede Kullanılan)
| Bileşen | Sürüm |
|---------|-------|
| Python | 3.12-slim |
| PostgreSQL | 16-alpine |
| Redis | 7-alpine |
| Django | 5.2.x |

### Oluşturulan Docker Dosyaları
```
v0/MAYSCON/mayscon.v1/infra/docker/
├── docker-compose.test.yml   🆕 Test ortamı
├── Dockerfile.test           🆕 Test image
├── docker-compose.yml        # Base (Redis, pgAdmin)
├── docker-compose.dev.yml    # Development
└── docker-compose.akademi.yml # Akademi DB'leri
```

### Test Script'i
```
v0/MAYSCON/mayscon.v1/scripts/
└── run_tests.sh              🆕 Test runner script
```

---

## 🚀 Hızlı Başlangıç

### 1. Docker Kurulumu (Mac/Windows/Linux)
```bash
# Docker Desktop'ı yükleyin
# https://www.docker.com/products/docker-desktop/
```

### 2. Test Ortamını Başlat
```bash
cd /Users/esat/Desktop/BelgeNet/v0/MAYSCON/mayscon.v1

# Script ile (önerilen)
./scripts/run_tests.sh up        # Servisleri başlat
./scripts/run_tests.sh collect   # Test listesi
./scripts/run_tests.sh           # Tüm testler
./scripts/run_tests.sh unit      # Sadece unit testler
./scripts/run_tests.sh down      # Servisleri durdur

# Veya manuel
cd infra/docker
docker-compose -f docker-compose.test.yml up -d
docker-compose -f docker-compose.test.yml run --rm test-runner pytest tests/akademi/ -v
```

### 3. Spesifik Testler
```bash
./scripts/run_tests.sh unit         # Unit testler
./scripts/run_tests.sh api          # API testler
./scripts/run_tests.sh integration  # Integration testler
./scripts/run_tests.sh permissions  # Permission testler
./scripts/run_tests.sh shell        # Container shell aç
```

### 4. Servisleri Durdur
```bash
./scripts/run_tests.sh down

# Veya
cd infra/docker
docker-compose -f docker-compose.test.yml down -v
```

---

## 📊 Portlar ve Credentials

| Servis | Port | Credentials |
|--------|------|-------------|
| PostgreSQL | 5440 | akademi / akademi_secret_2024 |
| Redis | 6379 | - |

### GitHub Actions Workflow
**Dosya:** `.github/workflows/tests.yml`

CI/CD pipeline zaten hazır:
- PostgreSQL ve Redis services
- Python 3.12 setup
- Dependencies install
- pytest çalıştırma
- Coverage report

---

## 📁 Oluşturulan Test Dosyaları

### Dizin Yapısı
```
v0/MAYSCON/mayscon.v1/tests/akademi/
├── conftest.py                    # Ana fixtures ✅
├── pytest.ini                     # Pytest config ✅
├── fixtures/
│   ├── factories.py               # Factory Boy ✅
│   └── helpers.py                 # Test helpers ✅
├── unit/
│   └── test_user_model.py         # 26 test ✅
├── api/
│   ├── test_auth_api.py           # 22 test ✅
│   ├── test_course_api.py         # 30 test ✅
│   ├── test_enrollment_api.py     # 18 test ✅
│   ├── test_student_api.py        # 17 test ✅
│   ├── test_instructor_api.py     # 15 test ✅
│   └── test_admin_api.py          # 18 test ✅
├── integration/
│   ├── test_audit_log.py          # 17 test ✅
│   ├── test_multi_tenant.py       # 20 test ✅
│   └── test_workflow.py           # 8 test ✅
└── permissions/
    └── test_permission_matrix.py  # 80+ test ✅
```

**Toplam: 291 test** (pytest --collect-only ile doğrulandı)

---

## 🔧 Local'de Karşılaşılan Sorunlar

### 1. Veritabanı Tabloları Yok
```
sqlite3.OperationalError: no such table: users_user
```
**Sebep:** Migration çalıştırılmamış
**Çözüm:** Docker ortamında `python manage.py migrate` çalıştırılmalı

### 2. Debug Toolbar Hatası
```
KeyError: 'djdt'
```
**Çözüm:** `settings_test.py`'de debug_toolbar devre dışı bırakıldı ✅

### 3. Monitor Middleware Hatası
```
NameError: name 'Text' is not defined
```
**Çözüm:** `settings_test.py`'de monitor middleware devre dışı bırakıldı ✅

---

## 📝 Docker Ortamında Yapılacaklar

### Öncelik 1: İlk Çalıştırma
1. [ ] Docker servislerini başlat
2. [ ] Bağımlılıkları yükle: `pip install -r tools/requirements/dev.txt`
3. [ ] Migration'ları çalıştır: `python manage.py migrate`
4. [ ] Test koleksiyonunu kontrol et: `pytest tests/akademi/ --collect-only`
5. [ ] Testleri çalıştır: `pytest tests/akademi/ -v`

### Öncelik 2: Hata Düzeltme
1. [ ] Başarısız testleri analiz et
2. [ ] API endpoint path'lerini doğrula (gerçek URL'lerle eşleşmeyebilir)
3. [ ] Factory model path'lerini doğrula
4. [ ] Fixture'ları düzelt

### Öncelik 3: Coverage
1. [ ] Coverage raporu oluştur: `pytest --cov=backend --cov-report=html`
2. [ ] %80 hedefini kontrol et
3. [ ] Eksik kapsam alanlarını tespit et

---

## 🔗 Referans Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `docs/new_updates/test_plan.md` | Master test planı |
| `docs/new_updates/todo_list_v2.md` | Detaylı todo listesi (tamamlandı) |
| `docs/new_updates/test_summary.md` | Proje özeti |
| `docs/new_updates/change_log.md` | Değişiklik kaydı |
| `docs/new_updates/next_steps.md` | Sonraki adımlar |

---

## 🚀 Hızlı Başlangıç (Docker İçin)

```bash
# Docker container içinde:

# 1. PYTHONPATH ayarla
export PYTHONPATH="/app/AKADEMI:/app"
export DJANGO_SETTINGS_MODULE=akademi.settings_test

# 2. Bağımlılıkları yükle
pip install -r tools/requirements/dev.txt

# 3. Migration
python manage.py migrate

# 4. Tüm testleri çalıştır
pytest tests/akademi/ -v --tb=short

# 5. Sadece belirli testler
pytest tests/akademi/unit/ -v                    # Unit testler
pytest tests/akademi/api/test_auth_api.py -v    # Auth testleri
pytest tests/akademi/ -m "tenant" -v            # Tenant testleri

# 6. Coverage ile
pytest tests/akademi/ --cov=backend --cov-report=term-missing
```

---

## 📊 Test Sonuçları (29 Aralık 2024)

### Son Çalıştırma

```
291 tests collected
209 passed (72%)
27 failed (9%)
55 skipped (19%)
```

### Docker'da Test Çalıştırma

```bash
# 1. Test container'larını başlat
cd v0/MAYSCON/mayscon.v1/infra/docker
docker-compose -f docker-compose.test.yml up -d test-db test-redis

# 2. Testleri çalıştır
docker-compose -f docker-compose.test.yml run --rm test-runner \
  sh -c "cd /app/MAYSCON && pytest tests/akademi/ -v --tb=short"

# 3. Container'ları kapat
docker-compose -f docker-compose.test.yml down
```

### Başarısız Testler Hakkında

| Kategori | Sebep |
|----------|-------|
| Password Test (1) | Test ortamında MD5 hasher kullanılıyor |
| API Tests (12) | Endpoint'ler farklı response dönüyor |
| Permission (4) | Users endpoint tüm auth kullanıcılara açık |
| Workflow (10) | Course create 403 vb. API davranış farkları |

---

## ⚠️ Önemli Notlar

1. **Virtual Environment:** Local'de oluşturulan `venv/` klasörü `.gitignore`'a eklenmelidir
2. **Settings:** Production'da `akademi.settings`, test'te `akademi.settings_test` kullanılmalı
3. **Database:** Test settings'de SQLite kullanılıyor, Docker'da PostgreSQL tercih edilebilir
4. **Paralel Test:** `pytest -n auto` ile paralel çalıştırma yapılabilir (pytest-xdist)
5. **Permission Matrix:** API'ler şu an tüm authenticated kullanıcılara açık - permission düzeltmeleri gerekiyor

---

**Son Güncelleme:** 29 Aralık 2024 - Testler Docker'da başarıyla çalıştırıldı ✅

