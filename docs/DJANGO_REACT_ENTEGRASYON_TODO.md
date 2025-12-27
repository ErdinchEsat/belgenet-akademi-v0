# 🔗 Django + React Entegrasyon Analizi ve Todo List

**Proje:** BelgeNet / Akademi İstanbul  
**Tarih:** 24 Aralık 2025  
**Durum:** Planlama Aşaması

---

## 📊 Mevcut Durum Analizi

### ✅ Hazır Olan Altyapı

| Bileşen | Durum | Açıklama |
|---------|-------|----------|
| Django Settings | ✅ | Modüler 16 dosya, kalıtım sistemi hazır |
| URL Yapısı | ✅ | API v1 routing mevcut (`/api/v1/`) |
| CSRF Trusted Origins | ✅ | `localhost:3000`, `localhost:5173` ekli |
| React Frontend | ✅ | 60+ bileşen, routing hazır |
| TypeScript Types | ✅ | User, Course, Tenant modelleri tanımlı |
| Context API | ✅ | AuthContext, TenantContext mevcut |

### ❌ Eksik/Tamamlanması Gereken

| Bileşen | Durum | Öncelik |
|---------|-------|---------|
| Django REST Framework | ❌ | 🔴 Kritik |
| JWT Authentication | ❌ | 🔴 Kritik |
| CORS Headers | ❌ | 🔴 Kritik |
| Backend API Apps | ❌ | 🔴 Kritik |
| Django User Model | ❌ | 🟡 Yüksek |
| API Client (Frontend) | ❌ | 🟡 Yüksek |
| OpenAPI/Swagger | ❌ | 🟢 Orta |

---

## 🏗️ Önerilen Mimari

### Strateji: **Ayrı Deployment + JWT Authentication**

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌──────────────┐         ┌──────────────┐                    │
│    │   Nginx      │         │   Nginx      │                    │
│    │   (Static)   │         │   (Proxy)    │                    │
│    │   :80/:443   │         │   :80/:443   │                    │
│    └──────┬───────┘         └──────┬───────┘                    │
│           │                        │                             │
│           ▼                        ▼                             │
│    ┌──────────────┐         ┌──────────────┐                    │
│    │   React      │  HTTPS  │   Django     │                    │
│    │   (Vite)     │◄───────►│   (Gunicorn) │                    │
│    │   Frontend   │  JSON   │   Backend    │                    │
│    │              │  API    │              │                    │
│    │  akademi.    │         │  api.        │                    │
│    │  example.com │         │  example.com │                    │
│    └──────────────┘         └──────┬───────┘                    │
│                                    │                             │
│                                    ▼                             │
│                             ┌──────────────┐                    │
│                             │  PostgreSQL  │                    │
│                             │  + Redis     │                    │
│                             └──────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Neden Bu Mimari?

1. **Bağımsız Ölçeklendirme:** Frontend ve Backend ayrı scale edilebilir
2. **CI/CD Kolaylığı:** Her biri bağımsız deploy edilebilir
3. **Teknoloji Esnekliği:** Her katman bağımsız güncellenebilir
4. **Güvenlik:** API gateway ile merkezi güvenlik kontrolü
5. **Performans:** CDN ile static asset dağıtımı

---

## 📝 TODO LIST

### FAZE 1: Backend Altyapı (Öncelik: 🔴 Kritik)

#### 1.1 Django REST Framework Kurulumu
- [ ] **1.1.1** DRF paketini requirements'a ekle
  ```txt
  # tools/requirements/api.txt (yeni dosya)
  djangorestframework>=3.15.0
  djangorestframework-simplejwt>=5.3.0
  drf-spectacular>=0.27.0
  django-cors-headers>=4.3.0
  django-filter>=24.0
  ```

- [ ] **1.1.2** MAYSCON settings'e DRF ayarlarını ekle
  ```python
  # config/settings/rest.py (yeni dosya)
  REST_FRAMEWORK = {
      'DEFAULT_AUTHENTICATION_CLASSES': [
          'rest_framework_simplejwt.authentication.JWTAuthentication',
          'rest_framework.authentication.SessionAuthentication',
      ],
      'DEFAULT_PERMISSION_CLASSES': [
          'rest_framework.permissions.IsAuthenticated',
      ],
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 20,
      'DEFAULT_FILTER_BACKENDS': [
          'django_filters.rest_framework.DjangoFilterBackend',
          'rest_framework.filters.SearchFilter',
          'rest_framework.filters.OrderingFilter',
      ],
      'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
  }
  ```

- [ ] **1.1.3** INSTALLED_APPS'e ekle
  ```python
  # config/settings/apps.py
  THIRD_PARTY_APPS += [
      'rest_framework',
      'rest_framework_simplejwt',
      'rest_framework_simplejwt.token_blacklist',
      'corsheaders',
      'django_filters',
      'drf_spectacular',
  ]
  ```

#### 1.2 CORS Yapılandırması
- [ ] **1.2.1** CORS middleware'i ekle
  ```python
  # config/settings/middleware.py
  MIDDLEWARE = [
      'corsheaders.middleware.CorsMiddleware',  # En üste ekle!
      'django.middleware.common.CommonMiddleware',
      # ... diğerleri
  ]
  ```

- [ ] **1.2.2** CORS ayarlarını tanımla
  ```python
  # config/settings/cors.py (yeni dosya)
  from .env import IS_DEVELOPMENT, IS_PRODUCTION

  if IS_DEVELOPMENT:
      CORS_ALLOW_ALL_ORIGINS = True
  else:
      CORS_ALLOWED_ORIGINS = [
          'https://akademi.example.com',
          'https://app.akademi.example.com',
      ]

  CORS_ALLOW_CREDENTIALS = True
  CORS_ALLOW_HEADERS = [
      'accept',
      'authorization',
      'content-type',
      'x-csrftoken',
      'x-requested-with',
  ]
  ```

#### 1.3 JWT Authentication
- [ ] **1.3.1** JWT ayarlarını tanımla
  ```python
  # config/settings/jwt.py (yeni dosya)
  from datetime import timedelta
  from .env import SECRET_KEY

  SIMPLE_JWT = {
      'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
      'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
      'ROTATE_REFRESH_TOKENS': True,
      'BLACKLIST_AFTER_ROTATION': True,
      'UPDATE_LAST_LOGIN': True,

      'ALGORITHM': 'HS256',
      'SIGNING_KEY': SECRET_KEY,
      'VERIFYING_KEY': None,

      'AUTH_HEADER_TYPES': ('Bearer',),
      'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
      'USER_ID_FIELD': 'id',
      'USER_ID_CLAIM': 'user_id',

      'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
      'TOKEN_TYPE_CLAIM': 'token_type',
      'TOKEN_USER_CLASS': 'rest_framework_simplejwt.models.TokenUser',

      # Token response'a ek bilgi ekle
      'TOKEN_OBTAIN_SERIALIZER': 'services.auth.serializers.CustomTokenObtainPairSerializer',
  }
  ```

- [ ] **1.3.2** JWT URL'lerini ekle
  ```python
  # config/urls/api/v1.py
  from rest_framework_simplejwt.views import (
      TokenObtainPairView,
      TokenRefreshView,
      TokenVerifyView,
  )

  urlpatterns += [
      path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
      path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
      path('auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
  ]
  ```

---

### FAZE 2: Django Apps & Models (Öncelik: 🔴 Kritik)

#### 2.1 Custom User Model
- [ ] **2.1.1** `akademi.backend` altında `users` app oluştur
  ```bash
  cd v0/AKADEMI
  python manage.py startapp users akademi.backend/users
  ```

- [ ] **2.1.2** Custom User model tanımla
  ```python
  # akademi.backend/users/models.py
  from django.contrib.auth.models import AbstractUser
  from django.db import models

  class User(AbstractUser):
      class Role(models.TextChoices):
          GUEST = 'GUEST', 'Misafir'
          STUDENT = 'STUDENT', 'Öğrenci'
          INSTRUCTOR = 'INSTRUCTOR', 'Eğitmen'
          TENANT_ADMIN = 'TENANT_ADMIN', 'Kurum Yöneticisi'
          SUPER_ADMIN = 'SUPER_ADMIN', 'Süper Admin'

      role = models.CharField(
          max_length=20,
          choices=Role.choices,
          default=Role.GUEST
      )
      avatar = models.URLField(blank=True, null=True)
      title = models.CharField(max_length=100, blank=True)
      tenant = models.ForeignKey(
          'tenants.Tenant',
          on_delete=models.SET_NULL,
          null=True, blank=True,
          related_name='users'
      )
      points = models.IntegerField(default=0)
      streak = models.IntegerField(default=0)

      class Meta:
          verbose_name = 'Kullanıcı'
          verbose_name_plural = 'Kullanıcılar'
  ```

- [ ] **2.1.3** settings'e ekle
  ```python
  # akademi/settings.py
  AUTH_USER_MODEL = 'users.User'
  ```

#### 2.2 Tenant (Akademi) Model
- [ ] **2.2.1** `tenants` app oluştur
- [ ] **2.2.2** Tenant model tanımla
  ```python
  # akademi.backend/tenants/models.py
  from django.db import models

  class Tenant(models.Model):
      class TenantType(models.TextChoices):
          MUNICIPALITY = 'Municipality', 'Belediye'
          CORPORATE = 'Corporate', 'Kurumsal'
          UNIVERSITY = 'University', 'Üniversite'

      name = models.CharField(max_length=200)
      slug = models.SlugField(unique=True)
      logo = models.URLField(blank=True)
      color = models.CharField(max_length=7, default='#4F46E5')
      type = models.CharField(
          max_length=20,
          choices=TenantType.choices
      )
      
      # Theme config
      sidebar_position = models.CharField(
          max_length=10,
          choices=[('left', 'Sol'), ('right', 'Sağ')],
          default='left'
      )
      sidebar_color = models.CharField(max_length=7, default='#1E293B')
      button_radius = models.CharField(max_length=20, default='rounded-md')

      # Limits
      storage_limit_gb = models.IntegerField(default=10)
      user_limit = models.IntegerField(default=100)
      
      # Modules
      module_live_class = models.BooleanField(default=True)
      module_quiz = models.BooleanField(default=True)
      module_exam = models.BooleanField(default=True)
      module_assignment = models.BooleanField(default=True)

      is_active = models.BooleanField(default=True)
      created_at = models.DateTimeField(auto_now_add=True)

      class Meta:
          verbose_name = 'Akademi'
          verbose_name_plural = 'Akademiler'
  ```

#### 2.3 Course & LMS Models
- [ ] **2.3.1** `courses` app oluştur
- [ ] **2.3.2** Course, Module, Content modelleri
- [ ] **2.3.3** Enrollment modeli (Öğrenci-Kurs ilişkisi)
- [ ] **2.3.4** Progress modeli (İlerleme takibi)

#### 2.4 Diğer LMS Modelleri
- [ ] **2.4.1** `assignments` app - Ödev yönetimi
- [ ] **2.4.2** `exams` app - Sınav/Quiz yönetimi
- [ ] **2.4.3** `live_sessions` app - Canlı ders yönetimi
- [ ] **2.4.4** `certificates` app - Sertifika yönetimi
- [ ] **2.4.5** `notifications` app - Bildirim sistemi

---

### FAZE 3: API Endpoints (Öncelik: 🟡 Yüksek)

#### 3.1 Auth API
- [ ] **3.1.1** Token obtain (login) endpoint
- [ ] **3.1.2** Token refresh endpoint
- [ ] **3.1.3** Logout (token blacklist) endpoint
- [ ] **3.1.4** Register endpoint
- [ ] **3.1.5** Password reset endpoints
- [ ] **3.1.6** Me (current user) endpoint

```python
# services/auth/views.py
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Mevcut kullanıcı bilgilerini döndür"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Yeni kullanıcı kaydı"""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(UserSerializer(user).data, status=201)
    return Response(serializer.errors, status=400)
```

#### 3.2 User API
- [ ] **3.2.1** User CRUD endpoints
- [ ] **3.2.2** User profile update
- [ ] **3.2.3** User preferences

#### 3.3 Tenant API
- [ ] **3.3.1** Tenant list (Super Admin)
- [ ] **3.3.2** Tenant detail
- [ ] **3.3.3** Tenant users list
- [ ] **3.3.4** Tenant stats

#### 3.4 Course API
- [ ] **3.4.1** Course list/create
- [ ] **3.4.2** Course detail/update/delete
- [ ] **3.4.3** Course modules
- [ ] **3.4.4** Course content
- [ ] **3.4.5** Course enrollment
- [ ] **3.4.6** Course progress

#### 3.5 Student API
- [ ] **3.5.1** My courses
- [ ] **3.5.2** My assignments
- [ ] **3.5.3** My exams
- [ ] **3.5.4** My grades
- [ ] **3.5.5** My certificates

#### 3.6 Instructor API
- [ ] **3.6.1** My teaching courses
- [ ] **3.6.2** Student management
- [ ] **3.6.3** Assignment grading
- [ ] **3.6.4** Live session management

---

### FAZE 4: Frontend API Entegrasyonu (Öncelik: 🟡 Yüksek)

#### 4.1 API Client Setup
- [ ] **4.1.1** Axios veya Fetch wrapper oluştur
  ```typescript
  // lib/api/client.ts
  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

  class ApiClient {
    private baseURL: string;
    private accessToken: string | null = null;

    constructor(baseURL: string) {
      this.baseURL = baseURL;
      this.accessToken = localStorage.getItem('access_token');
    }

    private async request<T>(
      endpoint: string,
      options: RequestInit = {}
    ): Promise<T> {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
        ...(this.accessToken && { Authorization: `Bearer ${this.accessToken}` }),
        ...options.headers,
      };

      const response = await fetch(`${this.baseURL}${endpoint}`, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        // Token expired, try refresh
        const refreshed = await this.refreshToken();
        if (refreshed) {
          return this.request(endpoint, options);
        }
        // Logout user
        this.logout();
        throw new Error('Session expired');
      }

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      return response.json();
    }

    async get<T>(endpoint: string): Promise<T> {
      return this.request<T>(endpoint, { method: 'GET' });
    }

    async post<T>(endpoint: string, data: unknown): Promise<T> {
      return this.request<T>(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
      });
    }

    // ... put, patch, delete methods
  }

  export const api = new ApiClient(API_BASE_URL);
  ```

- [ ] **4.1.2** Token yönetimi için service
  ```typescript
  // lib/api/auth.ts
  export const authService = {
    async login(email: string, password: string) {
      const response = await api.post<TokenResponse>('/auth/token/', {
        email,
        password,
      });
      
      localStorage.setItem('access_token', response.access);
      localStorage.setItem('refresh_token', response.refresh);
      
      return response;
    },

    async logout() {
      const refreshToken = localStorage.getItem('refresh_token');
      await api.post('/auth/logout/', { refresh: refreshToken });
      
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    },

    async getCurrentUser() {
      return api.get<User>('/auth/me/');
    },
  };
  ```

#### 4.2 AuthContext Güncellemesi
- [ ] **4.2.1** Mock login'i gerçek API'ye bağla
- [ ] **4.2.2** Token refresh mekanizması
- [ ] **4.2.3** Auto-logout on token expire

#### 4.3 API Hooks
- [ ] **4.3.1** `useCourses` hook
- [ ] **4.3.2** `useEnrollments` hook
- [ ] **4.3.3** `useAssignments` hook
- [ ] **4.3.4** `useExams` hook
- [ ] **4.3.5** `useLiveSessions` hook

```typescript
// hooks/useCourses.ts
import { useState, useEffect } from 'react';
import { api } from '@/lib/api/client';
import type { Course } from '@/types';

export function useCourses(filters?: CourseFilters) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchCourses = async () => {
      try {
        setLoading(true);
        const data = await api.get<Course[]>('/courses/', { params: filters });
        setCourses(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchCourses();
  }, [filters]);

  return { courses, loading, error };
}
```

#### 4.4 Environment Yapılandırması
- [ ] **4.4.1** `.env` dosyaları oluştur
  ```bash
  # .env.development
  VITE_API_URL=http://localhost:8000/api/v1
  VITE_WS_URL=ws://localhost:8000/ws
  
  # .env.production
  VITE_API_URL=https://api.akademi.example.com/api/v1
  VITE_WS_URL=wss://api.akademi.example.com/ws
  ```

---

### FAZE 5: OpenAPI & Dokümantasyon (Öncelik: 🟢 Orta)

#### 5.1 Swagger/OpenAPI Setup
- [ ] **5.1.1** drf-spectacular ayarları
  ```python
  # config/settings/openapi.py
  SPECTACULAR_SETTINGS = {
      'TITLE': 'Akademi İstanbul API',
      'DESCRIPTION': 'LMS Platform REST API',
      'VERSION': '1.0.0',
      'SERVE_INCLUDE_SCHEMA': False,
      'COMPONENT_SPLIT_REQUEST': True,
      'SCHEMA_PATH_PREFIX': r'/api/v[0-9]+',
  }
  ```

- [ ] **5.1.2** URL'lere ekle
  ```python
  # config/urls/api/v1.py
  from drf_spectacular.views import (
      SpectacularAPIView,
      SpectacularSwaggerView,
      SpectacularRedocView,
  )

  urlpatterns += [
      path('schema/', SpectacularAPIView.as_view(), name='schema'),
      path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
      path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
  ]
  ```

#### 5.2 API Dokümantasyonu
- [ ] **5.2.1** Endpoint açıklamaları
- [ ] **5.2.2** Request/Response örnekleri
- [ ] **5.2.3** Error kodları dokümantasyonu

---

### FAZE 6: Güvenlik & Performans (Öncelik: 🟢 Orta)

#### 6.1 Rate Limiting
- [ ] **6.1.1** DRF throttling ayarları
- [ ] **6.1.2** Login attempt limiting
- [ ] **6.1.3** API abuse protection

#### 6.2 Caching
- [ ] **6.2.1** Redis cache setup
- [ ] **6.2.2** API response caching
- [ ] **6.2.3** User session caching

#### 6.3 Monitoring
- [ ] **6.3.1** API request logging
- [ ] **6.3.2** Performance metrics
- [ ] **6.3.3** Error tracking (Sentry)

---

### FAZE 7: Real-time Features (Öncelik: 🟢 Düşük/İleri)

#### 7.1 WebSocket Setup (Django Channels)
- [ ] **7.1.1** Channels kurulumu
- [ ] **7.1.2** ASGI configuration
- [ ] **7.1.3** Redis channel layer

#### 7.2 Real-time Features
- [ ] **7.2.1** Live notifications
- [ ] **7.2.2** Chat system
- [ ] **7.2.3** Live class presence

---

## 📁 Önerilen Dosya Yapısı (Sonuç)

```
AKADEMI/
├── akademi/                       # Django Core
│   ├── settings.py
│   ├── urls.py
│   └── ...
│
├── akademi.backend/               # Backend Apps
│   ├── users/                     # User management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── permissions.py
│   │
│   ├── tenants/                   # Multi-tenancy
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── middleware.py
│   │
│   ├── courses/                   # Course management
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   └── filters.py
│   │
│   ├── enrollments/               # Enrollment management
│   ├── assignments/               # Assignment management
│   ├── exams/                     # Exam/Quiz management
│   ├── live_sessions/             # Live class management
│   ├── certificates/              # Certificate management
│   └── notifications/             # Notification system
│
├── akademi.frontend/              # React Frontend
│   ├── lib/
│   │   └── api/                   # API client & services
│   │       ├── client.ts
│   │       ├── auth.ts
│   │       ├── courses.ts
│   │       └── ...
│   │
│   ├── hooks/                     # Custom hooks
│   │   ├── useAuth.ts
│   │   ├── useCourses.ts
│   │   └── ...
│   │
│   ├── contexts/
│   │   ├── AuthContext.tsx        # Updated with real API
│   │   └── ...
│   │
│   └── ...
│
└── manage.py
```

---

## ⏱️ Tahmini Zaman Çizelgesi

| Faz | Süre | Öncelik |
|-----|------|---------|
| Faz 1: Backend Altyapı | 1 hafta | 🔴 |
| Faz 2: Models & Migrations | 1-2 hafta | 🔴 |
| Faz 3: API Endpoints | 2-3 hafta | 🟡 |
| Faz 4: Frontend Entegrasyon | 1-2 hafta | 🟡 |
| Faz 5: Dokümantasyon | 3-5 gün | 🟢 |
| Faz 6: Güvenlik & Performans | 1 hafta | 🟢 |
| Faz 7: Real-time (Opsiyonel) | 1-2 hafta | 🟢 |

**Toplam Tahmini Süre:** 6-10 hafta

---

## 🚀 Hızlı Başlangıç Komutları

```bash
# 1. Bağımlılıkları yükle
pip install djangorestframework djangorestframework-simplejwt django-cors-headers drf-spectacular django-filter

# 2. Migrations oluştur (User model eklendikten sonra)
python manage.py makemigrations
python manage.py migrate

# 3. Superuser oluştur
python manage.py createsuperuser

# 4. Backend'i başlat
python manage.py runserver

# 5. Frontend'i başlat (ayrı terminalde)
cd akademi.frontend
npm run dev
```

---

## 📚 Faydalı Kaynaklar

- [Django REST Framework Docs](https://www.django-rest-framework.org/)
- [SimpleJWT Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
- [drf-spectacular Docs](https://drf-spectacular.readthedocs.io/)
- [Django Channels](https://channels.readthedocs.io/)
- [React Query (TanStack Query)](https://tanstack.com/query/latest)

---

*Bu doküman, proje ilerledikçe güncellenmelidir.*

