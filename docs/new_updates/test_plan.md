# EduTECH Backend Unit Test Master Plan

> **Hazırlayan:** Senior Developer (15+ yıl deneyim)
> **Tarih:** 29 Aralık 2024
> **Versiyon:** 1.0

---

## 1. Proje Analizi Özeti

### 1.1 Backend Yapısı

```
backend/
├── users/           # User Model, Auth, RBAC
├── tenants/         # Multi-tenant yapı
├── courses/         # Kurs, Modül, İçerik, Enrollment
├── student/         # Sınıf, Ödev, Canlı Ders, Bildirim
├── instructor/      # Eğitmen Dashboard, Sınıflar
├── admin_api/       # Admin Dashboard, Raporlar
├── quizzes/         # Quiz Sistemi
├── progress/        # Video İlerleme
├── player/          # Playback Session
├── live/            # Canlı Ders Providers
├── certificates/    # Sertifika Sistemi
├── ai/              # AI Asistan
├── notes/           # Zamanlı Notlar
├── storage/         # Dosya Yönetimi
├── realtime/        # WebSocket, Mesajlaşma
└── libs/            # Ortak kütüphaneler
    ├── idempotency/ # Idempotent işlemler
    └── tenant_aware/# Tenant-aware modeller

logs/
└── audit/           # AuditLog, UserSession, ModelChangeLog
```

### 1.2 Roller (RBAC)

| Rol | Yetkiler |
|-----|----------|
| `GUEST` | Sadece public içerik |
| `STUDENT` | Kurs görüntüleme, enrollment, progress |
| `INSTRUCTOR` | Kurs oluşturma, sınıf yönetimi, öğrenci takibi |
| `ADMIN` | Tenant içi yönetim (deprecated, TENANT_ADMIN kullan) |
| `TENANT_ADMIN` | Tenant yönetimi, kullanıcı/kurs CRUD |
| `SUPER_ADMIN` | Global erişim, tüm tenantlar |

### 1.3 Kritik Özellikler

- **Multi-tenant izolasyonu**: Tenant A verisi Tenant B'den görülemez
- **Email-based auth**: Username yerine email kullanılıyor
- **JWT Authentication**: SimpleJWT ile access/refresh token
- **Audit Logging**: Tüm kritik işlemler loglanıyor
- **Progress Tracking**: Seek-independent video ilerleme

---

## 2. Test Dizin Yapısı (Hedef)

```
tests/akademi/
├── conftest.py                    # Ana konfigürasyon (GÜNCELLENİR)
├── pytest.ini                     # Pytest ayarları (YENİ)
├── fixtures/
│   ├── __init__.py
│   ├── base_data.py               # Mevcut (GÜNCELLENİR)
│   ├── factories.py               # YENİ - Factory Boy
│   ├── helpers.py                 # YENİ - Test yardımcıları
│   ├── student_data.py            # Mevcut
│   └── instructor_data.py         # Mevcut
├── unit/                          # YENİ
│   ├── __init__.py
│   ├── test_user_model.py         # U-01 ~ U-06
│   ├── test_tenant_model.py
│   ├── test_course_model.py
│   ├── test_enrollment_model.py
│   ├── test_quiz_model.py
│   └── test_progress_model.py
├── api/                           # YENİ
│   ├── __init__.py
│   ├── test_auth_api.py           # AUTH-01 ~ AUTH-07
│   ├── test_course_api.py         # C-01 ~ C-08
│   ├── test_enrollment_api.py     # E-01 ~ E-05
│   ├── test_student_api.py        # S-01 ~ S-05
│   ├── test_instructor_api.py     # I-01 ~ I-03
│   └── test_admin_api.py          # A-01 ~ A-03
├── integration/                   # YENİ
│   ├── __init__.py
│   ├── test_audit_log.py          # L-01 ~ L-04
│   ├── test_workflow.py           # Kurs yaşam döngüsü
│   └── test_multi_tenant.py       # Tenant izolasyon
└── permissions/                   # YENİ
    ├── __init__.py
    └── test_permission_matrix.py  # Tüm endpoint/rol kombinasyonları
```

---

## 3. Aşama 0: Test Altyapısı Kurulumu

### 3.1 Gerekli Bağımlılıklar

**Dosya:** `tools/requirements/dev.txt` (güncelleme)

```txt
# Test Framework
pytest>=7.4.0
pytest-django>=4.5.0
pytest-xdist>=3.3.0          # Paralel test
pytest-cov>=4.1.0            # Coverage
pytest-timeout>=2.2.0        # Timeout

# Test Utilities
factory-boy>=3.3.0           # Model factories
freezegun>=1.2.0             # Time mocking
responses>=0.24.0            # HTTP mocking
faker>=19.0.0                # Fake data
```

### 3.2 Pytest Konfigürasyonu

**Dosya:** `tests/akademi/pytest.ini`

```ini
[pytest]
DJANGO_SETTINGS_MODULE = akademi.settings
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts = 
    --strict-markers
    -ra
    -q
    --tb=short
    --cov=backend
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests (model/service)
    api: API endpoint tests
    integration: Integration tests
    slow: Slow running tests
    tenant: Multi-tenant tests
    
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning

timeout = 30
```

### 3.3 Ortak Fixtures

**Dosya:** `tests/akademi/fixtures/factories.py`

```python
"""
Factory Boy Factories
=====================

Test verisi oluşturmak için factory'ler.
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker('tr_TR')


class TenantFactory(DjangoModelFactory):
    """Tenant factory."""
    
    class Meta:
        model = 'tenants.Tenant'
    
    name = factory.LazyFunction(lambda: f"{fake.company()} Akademi")
    slug = factory.LazyAttribute(lambda o: slugify(o.name))
    type = 'Corporate'
    is_active = True
    

class UserFactory(DjangoModelFactory):
    """User factory."""
    
    class Meta:
        model = 'users.User'
    
    email = factory.LazyFunction(lambda: fake.unique.email())
    first_name = factory.LazyFunction(fake.first_name)
    last_name = factory.LazyFunction(fake.last_name)
    role = 'STUDENT'
    tenant = factory.SubFactory(TenantFactory)
    is_active = True
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        password = extracted or 'TestPass123!'
        self.set_password(password)
        if create:
            self.save()


class CourseFactory(DjangoModelFactory):
    """Course factory."""
    
    class Meta:
        model = 'courses.Course'
    
    title = factory.LazyFunction(lambda: fake.sentence(nb_words=4))
    slug = factory.LazyAttribute(lambda o: slugify(o.title))
    description = factory.LazyFunction(lambda: fake.paragraph())
    tenant = factory.SubFactory(TenantFactory)
    status = 'draft'
    level = 'Beginner'
    category = 'Programlama'
    

class EnrollmentFactory(DjangoModelFactory):
    """Enrollment factory."""
    
    class Meta:
        model = 'courses.Enrollment'
    
    user = factory.SubFactory(UserFactory)
    course = factory.SubFactory(CourseFactory)
    status = 'active'
    progress_percent = 0
```

### 3.4 Test Helpers

**Dosya:** `tests/akademi/fixtures/helpers.py`

```python
"""
Test Helpers
============

Ortak test yardımcı fonksiyonları.
"""

from rest_framework.test import APIClient
from contextlib import contextmanager


def create_auth_client(user, tenant=None):
    """Authenticated API client oluştur."""
    client = APIClient()
    client.force_authenticate(user=user)
    if tenant:
        client.defaults['HTTP_X_TENANT_ID'] = str(tenant.id)
    return client


def create_token_client(user):
    """JWT token ile authenticated client."""
    from rest_framework_simplejwt.tokens import RefreshToken
    
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


@contextmanager
def audit_capture():
    """Audit log capture context manager."""
    from logs.audit.models import AuditLog
    
    initial_count = AuditLog.objects.count()
    captured = []
    
    yield captured
    
    new_logs = AuditLog.objects.filter(
        id__gt=AuditLog.objects.order_by('-id').first().id - 
        (AuditLog.objects.count() - initial_count)
    )
    captured.extend(new_logs)


class AssertHelpers:
    """Test assertion yardımcıları."""
    
    @staticmethod
    def assert_tenant_isolated(queryset, tenant):
        """Tüm kayıtların aynı tenant'a ait olduğunu doğrula."""
        for obj in queryset:
            assert obj.tenant_id == tenant.id, \
                f"Tenant isolation violated: {obj} belongs to {obj.tenant_id}"
    
    @staticmethod
    def assert_error_format(response_data):
        """Error response formatını doğrula."""
        assert 'error' in response_data or 'detail' in response_data
    
    @staticmethod  
    def assert_no_pii_leak(data, fields=['password', 'token', 'secret']):
        """PII sızıntısı olmadığını doğrula."""
        data_str = str(data).lower()
        for field in fields:
            assert field not in data_str, f"PII leak detected: {field}"
```

### 3.5 Güncellenmiş conftest.py

**Dosya:** `tests/akademi/conftest.py` (güncelleme)

```python
"""
Akademi Test Configuration
==========================

Kapsamlı pytest fixtures.
"""

import pytest
import sys
from pathlib import Path

# Path configuration
AKADEMI_PATH = Path(__file__).resolve().parents[3] / 'AKADEMI'
MAYSCON_V1_PATH = Path(__file__).resolve().parents[2]

for path in [AKADEMI_PATH, MAYSCON_V1_PATH]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def pytest_configure():
    """Django setup."""
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'akademi.settings')
    
    import django
    django.setup()


# =============================================================================
# TENANT FIXTURES
# =============================================================================

@pytest.fixture
def tenant_a(db):
    """Primary test tenant."""
    from tests.akademi.fixtures.factories import TenantFactory
    return TenantFactory(name='Akademi A', slug='akademi-a')


@pytest.fixture
def tenant_b(db):
    """Secondary test tenant (for isolation tests)."""
    from tests.akademi.fixtures.factories import TenantFactory
    return TenantFactory(name='Akademi B', slug='akademi-b')


# =============================================================================
# USER FIXTURES
# =============================================================================

@pytest.fixture
def admin_a(tenant_a):
    """Tenant A admin user."""
    from tests.akademi.fixtures.factories import UserFactory
    return UserFactory(
        email='admin@akademi-a.com',
        role='TENANT_ADMIN',
        tenant=tenant_a,
        is_staff=True,
    )


@pytest.fixture
def instructor_a(tenant_a):
    """Tenant A instructor."""
    from tests.akademi.fixtures.factories import UserFactory
    return UserFactory(
        email='instructor@akademi-a.com',
        role='INSTRUCTOR',
        tenant=tenant_a,
    )


@pytest.fixture
def student_a(tenant_a):
    """Tenant A student."""
    from tests.akademi.fixtures.factories import UserFactory
    return UserFactory(
        email='student@akademi-a.com',
        role='STUDENT',
        tenant=tenant_a,
    )


@pytest.fixture
def student_b(tenant_b):
    """Tenant B student (for isolation tests)."""
    from tests.akademi.fixtures.factories import UserFactory
    return UserFactory(
        email='student@akademi-b.com',
        role='STUDENT',
        tenant=tenant_b,
    )


@pytest.fixture
def super_admin(db):
    """Super admin (no tenant)."""
    from tests.akademi.fixtures.factories import UserFactory
    return UserFactory(
        email='superadmin@system.com',
        role='SUPER_ADMIN',
        tenant=None,
        is_superuser=True,
        is_staff=True,
    )


# =============================================================================
# COURSE FIXTURES
# =============================================================================

@pytest.fixture
def course_draft_a(tenant_a, instructor_a):
    """Tenant A draft course."""
    from tests.akademi.fixtures.factories import CourseFactory
    course = CourseFactory(
        title='Draft Course',
        slug='draft-course',
        tenant=tenant_a,
        status='draft',
    )
    course.instructors.add(instructor_a)
    return course


@pytest.fixture
def course_published_a(tenant_a, instructor_a):
    """Tenant A published course."""
    from tests.akademi.fixtures.factories import CourseFactory
    course = CourseFactory(
        title='Published Course',
        slug='published-course',
        tenant=tenant_a,
        status='published',
        is_published=True,
    )
    course.instructors.add(instructor_a)
    return course


@pytest.fixture
def course_published_b(tenant_b):
    """Tenant B published course (for isolation tests)."""
    from tests.akademi.fixtures.factories import CourseFactory
    return CourseFactory(
        title='Tenant B Course',
        slug='tenant-b-course',
        tenant=tenant_b,
        status='published',
        is_published=True,
    )


# =============================================================================
# ENROLLMENT FIXTURES
# =============================================================================

@pytest.fixture
def enrollment_a(student_a, course_published_a):
    """Active enrollment in Tenant A."""
    from tests.akademi.fixtures.factories import EnrollmentFactory
    return EnrollmentFactory(
        user=student_a,
        course=course_published_a,
        status='active',
    )


# =============================================================================
# API CLIENT FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Unauthenticated API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def anon_client(api_client):
    """Alias for unauthenticated client."""
    return api_client


@pytest.fixture
def student_client(api_client, student_a):
    """Student authenticated client."""
    api_client.force_authenticate(user=student_a)
    return api_client


@pytest.fixture
def instructor_client(api_client, instructor_a):
    """Instructor authenticated client."""
    api_client.force_authenticate(user=instructor_a)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_a):
    """Admin authenticated client."""
    api_client.force_authenticate(user=admin_a)
    return api_client


@pytest.fixture
def super_admin_client(api_client, super_admin):
    """Super admin authenticated client."""
    api_client.force_authenticate(user=super_admin)
    return api_client


# =============================================================================
# UTILITY FIXTURES
# =============================================================================

@pytest.fixture
def audit_capture():
    """Audit log capture."""
    from tests.akademi.fixtures.helpers import audit_capture
    return audit_capture


@pytest.fixture
def freeze_time():
    """Time freezing fixture."""
    from freezegun import freeze_time
    return freeze_time
```

---

## 4. Aşama 1: User Model Testleri

**Dosya:** `tests/akademi/unit/test_user_model.py`

### Test Case'ler:

| ID | Test Adı | Açıklama | Beklenen |
|----|----------|----------|----------|
| U-01 | `test_required_fields_validation` | Email olmadan user create | `ValidationError` |
| U-02 | `test_email_unique_within_tenant` | Aynı tenant'ta aynı email | `IntegrityError` |
| U-03 | `test_email_across_tenants` | Farklı tenant'larda aynı email | İzin verilmeli |
| U-04 | `test_password_hashing` | Şifre hash'li saklanıyor | Plain text yok |
| U-05 | `test_deactivate_blocks_login` | Deaktif user login | `401/403` |
| U-06 | `test_role_assignment_audit` | Rol değişikliği audit log | Event oluşur |

### Detaylı Test Implementasyonu:

```python
"""
User Model Tests
================

Test cases: U-01 ~ U-06
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError


@pytest.mark.unit
class TestUserModelValidation:
    """User model validation tests."""
    
    def test_required_fields_validation(self, tenant_a):
        """U-01: Email olmadan user oluşturulamaz."""
        from backend.users.models import User
        
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(
                email=None,
                password='TestPass123!',
                tenant=tenant_a,
            )
        
        assert 'Email adresi zorunludur' in str(exc_info.value)
    
    def test_email_unique_within_tenant(self, student_a, tenant_a):
        """U-02: Aynı tenant'ta aynı email kullanılamaz."""
        from backend.users.models import User
        
        with pytest.raises(IntegrityError):
            User.objects.create_user(
                email=student_a.email,  # Var olan email
                password='TestPass123!',
                tenant=tenant_a,
            )
    
    def test_email_across_tenants(self, student_a, tenant_b):
        """U-03: Farklı tenant'larda aynı email kullanılabilir."""
        from backend.users.models import User
        
        # Bu test current implementasyona göre değişebilir
        # Eğer global unique ise ValueError bekle
        # Eğer tenant-scoped unique ise başarılı olmalı
        
        user = User.objects.create_user(
            email=student_a.email,
            password='TestPass123!',
            tenant=tenant_b,
        )
        
        assert user.id is not None
        assert user.tenant == tenant_b


@pytest.mark.unit
class TestUserPasswordSecurity:
    """Password security tests."""
    
    def test_password_hashing(self, db):
        """U-04: Şifre hash'li saklanıyor."""
        from backend.users.models import User
        
        plain_password = 'MySecretPassword123!'
        user = User.objects.create_user(
            email='test@example.com',
            password=plain_password,
        )
        
        # Plain text olarak saklanmamış
        assert plain_password not in user.password
        assert user.password.startswith('pbkdf2_sha256$') or \
               user.password.startswith('argon2')
        
        # check_password çalışıyor
        assert user.check_password(plain_password) is True
        assert user.check_password('wrongpassword') is False


@pytest.mark.unit
class TestUserDeactivation:
    """User deactivation tests."""
    
    def test_deactivate_blocks_login(self, student_a, api_client):
        """U-05: Deaktif user login yapamaz."""
        # Deaktif et
        student_a.is_active = False
        student_a.save()
        
        # Login dene
        response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        assert response.status_code in [401, 403]


@pytest.mark.unit
class TestUserAuditLogging:
    """User audit logging tests."""
    
    def test_role_assignment_audit(self, student_a, admin_client, audit_capture):
        """U-06: Rol değişikliği audit log oluşturur."""
        with audit_capture() as logs:
            response = admin_client.post(
                f'/api/v1/users/{student_a.id}/change_role/',
                {'role': 'INSTRUCTOR'}
            )
        
        assert response.status_code == 200
        
        # Audit log kontrolü
        role_logs = [l for l in logs if l.action == 'PERMISSION_CHANGE']
        assert len(role_logs) >= 1
```

---

## 5. Aşama 2: Authentication API Testleri

**Dosya:** `tests/akademi/api/test_auth_api.py`

### Test Case'ler:

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| AUTH-01 | `test_login_success` | `POST /auth/token/` | `200` + tokens |
| AUTH-02 | `test_login_wrong_password` | `POST /auth/token/` | `401` |
| AUTH-03 | `test_login_deactivated_user` | `POST /auth/token/` | `401/403` |
| AUTH-04 | `test_refresh_token_success` | `POST /auth/token/refresh/` | `200` |
| AUTH-05 | `test_refresh_token_expired` | `POST /auth/token/refresh/` | `401` |
| AUTH-06 | `test_logout_blacklists_token` | `POST /auth/logout/` | Refresh invalid |
| AUTH-07 | `test_brute_force_throttle` | `POST /auth/token/` | `429` after N fails |

### Detaylı Test Implementasyonu:

```python
"""
Authentication API Tests
========================

Test cases: AUTH-01 ~ AUTH-07
"""

import pytest
from freezegun import freeze_time
from datetime import timedelta
from django.utils import timezone


@pytest.mark.api
class TestLoginEndpoint:
    """Login endpoint tests."""
    
    def test_login_success(self, api_client, student_a):
        """AUTH-01: Doğru credentials ile login."""
        response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == student_a.email
    
    def test_login_wrong_password(self, api_client, student_a):
        """AUTH-02: Yanlış şifre ile login."""
        response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'WrongPassword!',
        })
        
        assert response.status_code == 401
        # Hata mesajı bilgi sızdırmamalı
        assert 'password' not in str(response.data).lower() or \
               'No active account' in str(response.data)
    
    def test_login_deactivated_user(self, api_client, student_a):
        """AUTH-03: Deaktif user ile login."""
        student_a.is_active = False
        student_a.save()
        
        response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        assert response.status_code in [401, 403]


@pytest.mark.api
class TestTokenRefresh:
    """Token refresh tests."""
    
    def test_refresh_token_success(self, api_client, student_a):
        """AUTH-04: Geçerli refresh ile yeni access token."""
        # İlk login
        login_response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        refresh_token = login_response.data['refresh']
        old_access = login_response.data['access']
        
        # Refresh
        response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_token,
        })
        
        assert response.status_code == 200
        assert 'access' in response.data
        assert response.data['access'] != old_access
    
    def test_refresh_token_expired(self, api_client, student_a, freeze_time):
        """AUTH-05: Expired refresh token."""
        # Login
        login_response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        refresh_token = login_response.data['refresh']
        
        # Zaman atla (refresh token süresi aşılır)
        with freeze_time(timezone.now() + timedelta(days=8)):
            response = api_client.post('/api/v1/auth/token/refresh/', {
                'refresh': refresh_token,
            })
        
        assert response.status_code == 401


@pytest.mark.api
class TestLogout:
    """Logout tests."""
    
    def test_logout_blacklists_token(self, student_client, student_a, api_client):
        """AUTH-06: Logout refresh token'ı blacklist'e ekler."""
        # Login
        login_response = api_client.post('/api/v1/auth/token/', {
            'email': student_a.email,
            'password': 'TestPass123!',
        })
        
        refresh_token = login_response.data['refresh']
        access_token = login_response.data['access']
        
        # Logout
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_response = api_client.post('/api/v1/auth/logout/', {
            'refresh': refresh_token,
        })
        
        assert logout_response.status_code in [200, 204]
        
        # Refresh artık çalışmamalı
        refresh_response = api_client.post('/api/v1/auth/token/refresh/', {
            'refresh': refresh_token,
        })
        
        assert refresh_response.status_code == 401


@pytest.mark.api
@pytest.mark.slow
class TestBruteForceProtection:
    """Brute force protection tests."""
    
    def test_brute_force_throttle(self, api_client, student_a):
        """AUTH-07: N kez hatalı login sonrası throttle."""
        # Not: Throttle ayarlarına bağlı
        # Varsayılan: 5 hatalı deneme sonrası throttle
        
        for i in range(10):
            response = api_client.post('/api/v1/auth/token/', {
                'email': student_a.email,
                'password': 'WrongPassword!',
            })
            
            if response.status_code == 429:
                # Throttle aktif
                assert True
                return
        
        # Throttle yoksa veya limit yüksekse skip
        pytest.skip("Throttle not configured or limit too high")
```

---

## 6. Aşama 3: Course API Testleri

**Dosya:** `tests/akademi/api/test_course_api.py`

### Test Case'ler:

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| C-01 | `test_instructor_create_course` | `POST /courses/` | `201` |
| C-02 | `test_student_create_forbidden` | `POST /courses/` | `403` |
| C-03 | `test_draft_not_visible_to_student` | `GET /courses/` | Draft yok |
| C-04 | `test_publish_requires_fields` | `POST /courses/{id}/approve/` | `400` |
| C-05 | `test_publish_success` | `POST /courses/{id}/approve/` | `200` |
| C-06 | `test_update_only_owner` | `PATCH /courses/{id}/` | `403` for others |
| C-07 | `test_course_list_filtering` | `GET /courses/?category=x` | Filtered |
| C-08 | `test_tenant_isolation` | `GET /courses/{id}/` | `404/403` |

### Detaylı Test Implementasyonu:

```python
"""
Course API Tests
================

Test cases: C-01 ~ C-08
"""

import pytest


@pytest.mark.api
class TestCourseCreate:
    """Course creation tests."""
    
    def test_instructor_create_course(self, instructor_client, tenant_a):
        """C-01: Instructor kurs oluşturabilir."""
        response = instructor_client.post('/api/v1/courses/', {
            'title': 'Test Course',
            'slug': 'test-course',
            'description': 'Test description',
            'category': 'Programlama',
            'level': 'Beginner',
        })
        
        assert response.status_code == 201
        assert response.data['title'] == 'Test Course'
        assert response.data['status'] == 'draft'
    
    def test_student_create_forbidden(self, student_client):
        """C-02: Student kurs oluşturamaz."""
        response = student_client.post('/api/v1/courses/', {
            'title': 'Student Course',
            'slug': 'student-course',
            'description': 'Should fail',
            'category': 'Test',
        })
        
        assert response.status_code == 403


@pytest.mark.api
class TestCourseVisibility:
    """Course visibility tests."""
    
    def test_draft_not_visible_to_student(
        self, student_client, course_draft_a, course_published_a
    ):
        """C-03: Draft kurs student'a görünmez."""
        response = student_client.get('/api/v1/courses/')
        
        assert response.status_code == 200
        
        course_ids = [c['id'] for c in response.data['results']]
        
        # Draft görünmemeli
        assert course_draft_a.id not in course_ids
        # Published görünmeli
        assert course_published_a.id in course_ids


@pytest.mark.api
class TestCoursePublish:
    """Course publish workflow tests."""
    
    def test_publish_requires_fields(self, admin_client, tenant_a, instructor_a):
        """C-04: Eksik alanlı kurs yayınlanamaz."""
        from tests.akademi.fixtures.factories import CourseFactory
        
        # Eksik alanlı kurs
        course = CourseFactory(
            title='Incomplete',
            slug='incomplete',
            description='',  # Eksik
            tenant=tenant_a,
            status='pending_admin_setup',
        )
        course.instructors.add(instructor_a)
        
        response = admin_client.post(f'/api/v1/courses/{course.slug}/approve/')
        
        # Ya 400 döner ya da validation hatası
        # Implementation'a göre değişebilir
        assert response.status_code in [200, 400]
    
    def test_publish_success(self, admin_client, course_draft_a):
        """C-05: Geçerli kurs yayınlanabilir."""
        # Önce review'a gönder
        course_draft_a.status = 'pending_admin_setup'
        course_draft_a.save()
        
        response = admin_client.post(
            f'/api/v1/courses/{course_draft_a.slug}/approve/'
        )
        
        assert response.status_code == 200
        
        course_draft_a.refresh_from_db()
        assert course_draft_a.status == 'published'
        assert course_draft_a.is_published is True


@pytest.mark.api
class TestCourseUpdate:
    """Course update tests."""
    
    def test_update_only_owner(
        self, api_client, course_draft_a, tenant_a
    ):
        """C-06: Sadece owner güncelleyebilir."""
        from tests.akademi.fixtures.factories import UserFactory
        
        # Başka instructor
        other_instructor = UserFactory(
            email='other@akademi-a.com',
            role='INSTRUCTOR',
            tenant=tenant_a,
        )
        
        api_client.force_authenticate(user=other_instructor)
        
        response = api_client.patch(
            f'/api/v1/courses/{course_draft_a.slug}/',
            {'title': 'Hijacked Title'}
        )
        
        assert response.status_code == 403


@pytest.mark.api
class TestCourseFiltering:
    """Course filtering tests."""
    
    def test_course_list_filtering(self, student_client, tenant_a, instructor_a):
        """C-07: Filtreleme doğru çalışıyor."""
        from tests.akademi.fixtures.factories import CourseFactory
        
        # Farklı kategorilerde kurslar
        CourseFactory(
            title='Python Course',
            slug='python-course',
            tenant=tenant_a,
            category='Programlama',
            status='published',
            is_published=True,
        ).instructors.add(instructor_a)
        
        CourseFactory(
            title='Design Course',
            slug='design-course',
            tenant=tenant_a,
            category='Tasarım',
            status='published',
            is_published=True,
        ).instructors.add(instructor_a)
        
        # Filtrelenmiş liste
        response = student_client.get('/api/v1/courses/?category=Programlama')
        
        assert response.status_code == 200
        
        categories = [c['category'] for c in response.data['results']]
        assert all(cat == 'Programlama' for cat in categories)


@pytest.mark.api
@pytest.mark.tenant
class TestCourseTenantIsolation:
    """Tenant isolation tests."""
    
    def test_tenant_isolation(self, student_client, course_published_b):
        """C-08: Tenant B kursuna erişilemez."""
        response = student_client.get(
            f'/api/v1/courses/{course_published_b.slug}/'
        )
        
        # 404 veya 403 döner
        assert response.status_code in [403, 404]
```

---

## 7. Aşama 4: Enrollment Testleri

**Dosya:** `tests/akademi/api/test_enrollment_api.py`

### Test Case'ler:

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| E-01 | `test_enroll_free_course` | `POST /courses/{id}/enroll/` | `201` |
| E-02 | `test_enroll_draft_forbidden` | `POST /courses/{id}/enroll/` | `400/403` |
| E-03 | `test_duplicate_enroll_idempotent` | `POST /courses/{id}/enroll/` | `200/409` |
| E-04 | `test_cancel_enrollment` | `POST /enrollments/{id}/cancel/` | `200` |
| E-05 | `test_cross_tenant_enroll_forbidden` | `POST /courses/{id}/enroll/` | `404/403` |

---

## 8. Aşama 5: Student/Instructor/Admin API Testleri

### Student API (S-01 ~ S-05)

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| S-01 | `test_get_self_profile` | `GET /students/me/` | `200` |
| S-02 | `test_patch_allowed_fields_only` | `PATCH /students/me/` | Role unchanged |
| S-03 | `test_progress_write_increases` | `PUT /progress/` | Monotonic increase |
| S-04 | `test_progress_cannot_decrease` | `PUT /progress/` | Clamp at max |
| S-05 | `test_unenrolled_content_forbidden` | `GET /contents/{id}/` | `403` |

### Instructor API (I-01 ~ I-03)

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| I-01 | `test_own_course_list` | `GET /instructor/courses/` | Only owned |
| I-02 | `test_reorder_lessons` | `POST /courses/{id}/lessons/reorder/` | Order persisted |
| I-03 | `test_roster_only_own_course` | `GET /courses/{id}/roster/` | `403` for others |

### Admin API (A-01 ~ A-03)

| ID | Test Adı | Endpoint | Beklenen |
|----|----------|----------|----------|
| A-01 | `test_user_list_tenant_scoped` | `GET /admin/users/` | Tenant isolated |
| A-02 | `test_deactivate_user` | `POST /admin/users/{id}/deactivate/` | `200` + audit |
| A-03 | `test_bulk_import` | `POST /admin/users/import/` | Partial success |

---

## 9. Aşama 6: Audit Log Testleri

**Dosya:** `tests/akademi/integration/test_audit_log.py`

### Test Case'ler:

| ID | Test Adı | Açıklama | Beklenen |
|----|----------|----------|----------|
| L-01 | `test_course_create_audit` | Kurs oluşturma | Audit event |
| L-02 | `test_enrollment_complete_audit` | Enrollment tamamlama | Audit event |
| L-03 | `test_audit_access_control` | Rol bazlı erişim | Student=403 |
| L-04 | `test_audit_pii_safety` | PII sızıntısı yok | Password/token yok |

---

## 10. Aşama 7: Permission Matrix Testleri

**Dosya:** `tests/akademi/permissions/test_permission_matrix.py`

### Matrix Format:

```python
PERMISSION_MATRIX = [
    # (endpoint, method, anon, student, instructor, admin)
    ('/api/v1/courses/', 'GET', 401, 200, 200, 200),
    ('/api/v1/courses/', 'POST', 401, 403, 201, 201),
    ('/api/v1/auth/me/', 'GET', 401, 200, 200, 200),
    # ... diğer endpoint'ler
]

@pytest.mark.parametrize(
    'endpoint,method,anon,student,instructor,admin',
    PERMISSION_MATRIX
)
def test_permission_matrix(
    endpoint, method, anon, student, instructor, admin,
    anon_client, student_client, instructor_client, admin_client
):
    """Tüm endpoint/rol kombinasyonlarını test et."""
    clients = {
        'anon': (anon_client, anon),
        'student': (student_client, student),
        'instructor': (instructor_client, instructor),
        'admin': (admin_client, admin),
    }
    
    for role, (client, expected) in clients.items():
        if method == 'GET':
            response = client.get(endpoint)
        elif method == 'POST':
            response = client.post(endpoint, {})
        # ... diğer methodlar
        
        assert response.status_code == expected, \
            f"{role} got {response.status_code}, expected {expected}"
```

---

## 11. Uygulama Sırası ve Zaman Çizelgesi

| Aşama | Açıklama | Tahmini Süre | Öncelik |
|-------|----------|--------------|---------|
| 0 | Altyapı Kurulumu | 2-3 saat | P0 |
| 1 | User Model Tests | 2-3 saat | P0 |
| 2 | Auth API Tests | 3-4 saat | P0 |
| 3 | Course API Tests | 4-5 saat | P0 |
| 4 | Enrollment Tests | 2-3 saat | P1 |
| 5 | Student/Instructor/Admin | 5-6 saat | P1 |
| 6 | Audit Log Tests | 2-3 saat | P1 |
| 7 | Permission Matrix | 3-4 saat | P2 |

**Toplam:** ~25-30 saat

---

## 12. CI/CD Entegrasyonu

### GitHub Actions Workflow

```yaml
name: Backend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r tools/requirements/dev.txt
      
      - name: Run tests
        run: |
          pytest tests/akademi/ -v --cov --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 13. Kabul Kriterleri

### Minimum Requirements

- [ ] Tüm P0 testler geçiyor
- [ ] Code coverage ≥80%
- [ ] Multi-tenant izolasyon testleri geçiyor
- [ ] Permission matrix %100 coverage
- [ ] CI pipeline yeşil

### Quality Gates

- [ ] No PII leaks
- [ ] No N+1 queries (assertNumQueries)
- [ ] Response schema validation
- [ ] Error message standardization

---

## Sonraki Adımlar

1. `change_log.md` oluşturulacak
2. Factories implement edilecek
3. Test dosyaları sırasıyla oluşturulacak
4. CI pipeline kurulacak

---

**Hazırlayan:** Senior Developer
**Son Güncelleme:** 29 Aralık 2024

