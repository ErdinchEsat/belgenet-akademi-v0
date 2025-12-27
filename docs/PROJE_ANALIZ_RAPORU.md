# 📊 BelgeNet Proje Analiz Raporu

**Rapor Tarihi:** 24 Aralık 2025  
**Analiz Yapan:** Claude AI  
**Proje Konumu:** `/mnt/c/Users/asringlobal/Desktop/BelgeNet`

---

## 📁 Üst Düzey Dizin Yapısı

```
BelgeNet/
├── todo.md                    # Proje todo notları
└── v0/                        # Ana versiyon klasörü
    ├── AKADEMI/               # ✅ AKTİF - Eğitim Yönetim Sistemi (LMS)
    ├── BELGENET/              # 📝 BOŞ - Gelecekteki modül
    ├── MAYSCON/               # ✅ AKTİF - Merkezi Django Framework
    ├── MUSTERI/               # 📝 BOŞ - Gelecekteki modül  
    └── SOZLESME/              # 📝 BOŞ - Gelecekteki modül
```

---

## 🏛️ Mimari Genel Bakış

Proje, **modüler monolith** mimarisi üzerine kurulmuştur. İki ana aktif modül bulunmaktadır:

1. **MAYSCON (mayscon.v1):** Merkezi Django Framework - Tüm projelerin kalıtım aldığı temel altyapı
2. **AKADEMI:** LMS uygulaması - MAYSCON'dan kalıtım alan ilk müşteri projesi

### Kalıtım Modeli

```
┌─────────────────────────────────────────────────────────────┐
│                    MAYSCON (mayscon.v1)                     │
│              Merkezi Django Enterprise Framework            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Config  │ │ Infra   │ │ Logs    │ │ Tools   │           │
│  │ Settings│ │ Docker  │ │ Monitor │ │ CLI     │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
└───────┼──────────┼──────────┼──────────┼───────────────────┘
        │          │          │          │
        ▼          ▼          ▼          ▼
┌─────────────────────────────────────────────────────────────┐
│                       AKADEMI                                │
│                 Eğitim Yönetim Sistemi                       │
│  ┌────────────────────┐  ┌────────────────────────┐         │
│  │  akademi (Django)  │  │  akademi.frontend      │         │
│  │  - settings.py     │  │  - React 18 + TS       │         │
│  │  - urls.py         │  │  - Vite                │         │
│  │  - wsgi/asgi       │  │  - Tailwind CSS        │         │
│  └────────────────────┘  └────────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 MAYSCON - Merkezi Framework Analizi

### Proje Kimliği

| Özellik | Değer |
|---------|-------|
| **Paket Adı** | asrin-core |
| **Versiyon**  | 1.0.0 |
| **Python**    | >=3.11 |
| **Django**    | >=5.2, <6.0 |
| **Lisans**    | Proprietary (Asrın Global) |

### Dizin Yapısı

```
mayscon.v1/
├── config/                    # 🔧 Merkezi Konfigürasyon
│   ├── hub/                   # Django core (settings, urls, wsgi/asgi)
│   ├── settings/              # Modüler settings (16 dosya)
│   │   ├── __init__.py        # Tüm settings'i birleştiren ana modül
│   │   ├── env.py             # Environment değişkenleri
│   │   ├── base.py            # Temel ayarlar
│   │   ├── security.py        # Güvenlik (HTTPS, HSTS, CSRF)
│   │   ├── apps.py            # INSTALLED_APPS
│   │   ├── middleware.py      # Middleware zinciri
│   │   ├── templates.py       # Template engine
│   │   ├── static.py          # Static/Media dosyalar
│   │   ├── data.py            # Database (Multi-DB desteği)
│   │   ├── cache.py           # Redis cache
│   │   ├── auth.py            # Authentication
│   │   ├── i18n.py            # Internationalization
│   │   ├── logging.py         # Logging sistemi
│   │   ├── url_config.py      # URL yapılandırması
│   │   ├── dev.py             # Development override
│   │   └── prod.py            # Production override
│   ├── urls/                  # Modüler URL yönetimi
│   └── startup.py             # Startup banner sistemi
│
├── infra/                     # 🐳 Altyapı & DevOps
│   ├── aws/                   # AWS konfigürasyonları
│   ├── data/                  # Veri dosyaları
│   ├── docker/                # Docker compose dosyaları
│   ├── env/                   # Environment (.env) dosyaları
│   ├── gunicorn/              # Gunicorn WSGI konfigürasyonları
│   ├── k8s/                   # Kubernetes manifestleri
│   └── nginx/                 # Nginx reverse proxy
│
├── logs/                      # 📋 Log Yönetim Sistemi
│   ├── analytics/             # Log analytics app
│   ├── audit/                 # Audit log app
│   ├── utils/                 # Log yardımcı araçları
│   └── viewer/                # Log viewer app
│
├── secure/                    # 🔐 Güvenlik Modülü
│   ├── passwords.py           # Şifre yönetimi
│   ├── tokens.py              # Token yönetimi
│   └── validators.py          # Doğrulayıcılar
│
├── services/                  # 🔌 Mikro-servis Yapısı
│   ├── admin/                 # Admin servisi
│   └── api/                   # API servisi
│
├── tools/                     # 🛠️ Yardımcı Araçlar
│   ├── cli/                   # CLI komutları (init, update, sync)
│   ├── db/                    # Database routers
│   ├── logs/                  # Custom logging handlers
│   ├── management/            # Django management commands
│   ├── menu/                  # İnteraktif terminal menü
│   ├── monitor/               # Unified monitoring system
│   └── requirements/          # Pip requirements
│
├── webapp/                    # 🌐 Web Uygulaması
│   ├── core/                  # Core app
│   ├── home/                  # Ana sayfa app
│   ├── manage.py              # Django CLI
│   ├── media/                 # Kullanıcı yüklemeleri
│   ├── static/                # Static assets
│   └── templates/             # HTML templates
│
├── locale/                    # 🌍 Çeviri dosyaları
├── tests/                     # 🧪 Test dosyaları
├── makefile                   # Build automation
├── pyproject.toml             # Python paket konfigürasyonu
└── README.md                  # Dokümantasyon
```

### Temel Özellikler

#### 1. Modüler Settings Sistemi
- **16 ayrı settings modülü** ile endişelerin ayrımı (Separation of Concerns)
- Environment bazlı otomatik override (dev/staging/prod)
- Kalıtım için tasarlanmış mimari

#### 2. Multi-Database Desteği
- Primary, Replica, Analytics, Logs ayrımı
- Otomatik read/write yönlendirme (Database Routers)

#### 3. Gelişmiş Logging
- Seviye bazlı log ayrımı (DEBUG, INFO, WARNING, ERROR)
- Renkli console output (Colorama)
- Log analytics ve dashboard

#### 4. DevOps Hazır
- Docker Compose (Dev & Prod)
- Kubernetes manifestleri
- Nginx reverse proxy
- Gunicorn WSGI server

#### 5. Makefile Komutları

| Kategori          | Komut             | Açıklama                      |
|----------         |-------            |----------                     |
| **Başlangıç**     | `make dev`        | Geliştirme ortamını başlat    |
|                   | `make dev-nginx`  | Nginx + Gunicorn stack        |
|                   | `make stop`       | Servisleri durdur             |
| **İzleme**        | `make monitor`    | Terminal monitor              |
|                   | `make monitor-web`| Web dashboard (:9000)         |
|                   | `make logs`       | Container logları             |
| **Araçlar**       | `make shell`      | Container bash                |
|                   | `make pgadmin`    | pgAdmin4 (:5050)              |
|                   | `make mailhog`    | Mail test (:8025)             |
| **Veritabanı**    | `make migrate`    | Migration çalıştır            |
|                   | `make backup`     | Backup al                     |
|                   | `make restore`    | Restore yap                   |
| **Core**          | `make core-init`  | Yeni proje oluştur            |
|                   | `make core-update`| Merkezi güncelleme            |
|                   | `make core-sync`  | Projeleri senkronize et       |

### Bağımlılıklar

```toml
# Core
Django>=5.2,<6.0
python-decouple>=3.8
psycopg2-binary>=2.9.9
redis>=5.0
gunicorn>=21.0
whitenoise>=6.6

# Dev
django-extensions>=3.2
django-debug-toolbar>=4.2
ipython>=8.0
pytest>=7.4
black>=23.0

# Prod
sentry-sdk>=1.32
django-storages>=1.14
boto3>=1.28
```

---

## 🎓 AKADEMI - LMS Analizi

### Proje Kimliği

| Özellik           | Değer                     |
|---------          |-------                    |
| **Proje Adı**     | Akademi İstanbul          |
| **Tip**           | Multi-tenant LMS          |
| **Frontend**      | React 18 + TypeScript + Vite |
| **Backend**       | Django (MAYSCON'dan kalıtım) |
| **Port**          | Frontend: 3000, Backend: 8000 |

### Dizin Yapısı

```
AKADEMI/
├── akademi/                   # 🐍 Django Backend Core
│   ├── __init__.py
│   ├── asgi.py               # ASGI application
│   ├── settings.py           # MAYSCON'dan kalıtım + override'lar
│   ├── urls.py               # URL routing
│   └── wsgi.py               # WSGI application
│
├── akademi.backend/          # 📝 Backend Apps (BOŞ - Geliştirilecek)
│
├── akademi.frontend/         # ⚛️ React Frontend
│   ├── components/           # Yeniden kullanılabilir UI bileşenleri
│   │   ├── layout/           # Sidebar, Header, ModalWrapper
│   │   │   ├── GlobalCalendarModal.tsx
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   └── ui/               # Temel UI elemanları
│   │       ├── Avatar.tsx
│   │       ├── Button.tsx
│   │       ├── GenericTable.tsx
│   │       ├── LiveSessionCard.tsx
│   │       └── UniversalCourseCard.tsx
│   │
│   ├── contexts/             # Global State Management
│   │   ├── AuthContext.tsx   # Kimlik doğrulama
│   │   └── TenantContext.tsx # Multi-tenancy
│   │
│   ├── features/             # Feature-based Architecture
│   │   ├── admin/            # Yönetici modülü
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   │   ├── super/    # Super Admin sayfaları
│   │   │   │   │   ├── TenantsPage.tsx
│   │   │   │   │   ├── GlobalUsersPage.tsx
│   │   │   │   │   ├── FinancePage.tsx
│   │   │   │   │   ├── SystemLogsPage.tsx
│   │   │   │   │   ├── SecurityPage.tsx
│   │   │   │   │   ├── AllCoursesPage.tsx
│   │   │   │   │   └── AllLiveSessionsPage.tsx
│   │   │   │   ├── SuperAdminDashboard.tsx
│   │   │   │   ├── TenantManagerDashboard.tsx
│   │   │   │   ├── TenantUsersPage.tsx
│   │   │   │   ├── TenantRolesPage.tsx
│   │   │   │   ├── TenantClassesPage.tsx
│   │   │   │   ├── TenantCourseCatalogPage.tsx
│   │   │   │   ├── TenantReportsPage.tsx
│   │   │   │   ├── TenantOpsInboxPage.tsx
│   │   │   │   └── TenantThemePage.tsx
│   │   │   └── services/
│   │   │
│   │   ├── core/             # Çekirdek sayfalar
│   │   │   └── pages/
│   │   │       ├── LandingPage.tsx
│   │   │       ├── AcademySelection.tsx
│   │   │       ├── DashboardHome.tsx
│   │   │       └── ProfilePage.tsx
│   │   │
│   │   └── lms/              # LMS modülü
│   │       ├── components/
│   │       │   ├── CompactCourseCard.tsx
│   │       │   ├── InfiniteCardStack.tsx
│   │       │   ├── LiveClassPrepDrawer.tsx
│   │       │   ├── QuickActionDrawer.tsx
│   │       │   ├── StudentAssignmentDrawer.tsx
│   │       │   └── student/
│   │       ├── mock/         # Mock data
│   │       ├── pages/
│   │       │   ├── CoursePlayer.tsx
│   │       │   ├── DashboardStudent.tsx
│   │       │   ├── DashboardInstructor.tsx
│   │       │   ├── instructor/
│   │       │   │   ├── CreateCoursePage.tsx
│   │       │   │   ├── LiveClassManager.tsx
│   │       │   │   ├── AssignmentManager.tsx
│   │       │   │   ├── QuizManager.tsx
│   │       │   │   ├── ExamManager.tsx
│   │       │   │   ├── MyCoursesPage.tsx
│   │       │   │   ├── MyStudentsPage.tsx
│   │       │   │   ├── MyClassesPage.tsx
│   │       │   │   ├── LessonCalendarPage.tsx
│   │       │   │   ├── InstructorAssessmentsPage.tsx
│   │       │   │   ├── BehaviorAnalysisPage.tsx
│   │       │   │   └── LiveStreamInterface.tsx
│   │       │   └── student/
│   │       │       ├── StudentClassesPage.tsx
│   │       │       ├── StudentClassDetailPage.tsx
│   │       │       ├── StudentCoursesPage.tsx
│   │       │       ├── StudentCourseDetailPage.tsx
│   │       │       ├── StudentLiveClassesPage.tsx
│   │       │       ├── StudentAssignmentsPage.tsx
│   │       │       ├── StudentExamsPage.tsx
│   │       │       ├── StudentGradesPage.tsx
│   │       │       ├── StudentCertificatesPage.tsx
│   │       │       ├── StudentCalendarPage.tsx
│   │       │       ├── StudentNotificationsPage.tsx
│   │       │       ├── StudentMessagesPage.tsx
│   │       │       └── StudentSupportPage.tsx
│   │       └── services/
│   │
│   ├── layouts/              # Sayfa düzenleri
│   ├── lib/                  # Yardımcı fonksiyonlar
│   ├── types/                # TypeScript arayüzleri
│   │   └── index.ts
│   │
│   ├── App.tsx               # Ana routing & providers
│   ├── index.tsx             # Entry point
│   ├── index.html            # HTML template
│   ├── vite.config.ts        # Vite konfigürasyonu
│   ├── tsconfig.json         # TypeScript config
│   ├── package.json          # NPM dependencies
│   ├── README.md             # Frontend dokümantasyonu
│   └── specification.md      # Teknik spesifikasyon
│
└── manage.py                 # Django CLI
```

### Frontend Teknoloji Stack

| Teknoloji         | Versiyon          | Amaç          |
|-----------        |----------         |------         |
| React             | ^18.2.0           | UI library    |
| TypeScript        | ~5.8.2            | Type safety   |
| Vite              | ^6.2.0            | Build tool    |
| React Router      | 6.23.0            | Routing       |
| Tailwind CSS      | -                 | Styling (Tailwind Merge) |
| Lucide React      | 0.378.0           | Icons         |
| Recharts          | 2.12.7            | Charts        |
| clsx              | 2.1.1             | Class utilities |

### Kullanıcı Rolleri

```typescript
enum UserRole {
  GUEST = 'GUEST',
  STUDENT = 'STUDENT',
  INSTRUCTOR = 'INSTRUCTOR',
  ADMIN = 'ADMIN',
  TENANT_ADMIN = 'TENANT_ADMIN',
  SUPER_ADMIN = 'SUPER_ADMIN'
}
```

#### 1. Öğrenci (STUDENT)
- Dashboard: Canlı dersler, son izlenenler, ödev takibi
- Eğitimlerim: Kayıtlı kurslar ve ilerleme
- Canlı Dersler: Zoom/Meet entegrasyonu
- Ödevler & Sınavlar: Yükleme ve katılım
- Sertifikalar & Transkript

#### 2. Eğitmen (INSTRUCTOR)
- Dashboard: Yaklaşan dersler, hızlı aksiyonlar
- Kurs Yönetimi: 4 adımlı wizard ile içerik oluşturma
- Canlı Ders Planlama
- Quiz/Sınav Oluşturma (AI destekli)
- Öğrenci Takibi & Performans Analizi

#### 3. Kurum Yöneticisi (TENANT_ADMIN)
- Kullanıcı Yönetimi: Rol atama, davet
- Kurs Kataloğu: Onay/Red akışı
- Raporlar: Eğitmen ve akademi performansı
- Tema Yönetimi: Kurumsal özelleştirme

#### 4. Süper Admin (SUPER_ADMIN)
- Altyapı İzleme: CPU, RAM, Disk
- Tenant Yönetimi: Yeni akademi oluşturma
- Global Kullanıcı Havuzu
- Finans: Ciro, hakediş
- Güvenlik: Tehdit izleme, loglar

### Multi-Tenancy Yapısı

```typescript
interface Tenant {
  id: string;
  name: string;
  slug: string;              // URL yapısı (örn: ibb-tech)
  logo: string;
  color: string;
  type: 'Municipality' | 'Corporate' | 'University';
  themeConfig: ThemeConfig;
}

interface ThemeConfig {
  sidebarPosition: 'left' | 'right';
  sidebarColor: string;
  sidebarContentColor: string;
  mainBackgroundColor: string;
  buttonRadius: 'rounded-md' | 'rounded-xl' | 'rounded-full' | 'rounded-none';
}
```

### Kurs Veri Modeli

```typescript
interface Course {
  id: string;
  title: string;
  description: string;
  coverUrl: string;
  category: string;
  language: string;
  level: 'Beginner' | 'Intermediate' | 'Advanced';
  tags: string[];
  instructors: { id: string; name: string; avatar?: string; }[];
  curriculum: { modules: CourseModule[]; };
  stats: { enrolled: number; rating: number; totalDuration: string; };
  pricing: { isFree: boolean; price: number; currency: 'TRY' | 'USD' | 'EUR'; };
  publish: { visibility: 'public' | 'private' | 'unlisted'; isPublished: boolean; };
  completion: { certificateEnabled: boolean; completionPercent: number; };
  status: 'draft' | 'pending_admin_setup' | 'needs_revision' | 'published' | 'archived';
}
```

### Routing Yapısı

| Route             | Sayfa             | Rol           |
|-------            |-------            |-----          |
| `/`               | Landing Page      | Public        |
| `/akademi-secimi` | Akademi Seçimi    | Public        |
| `/dashboard`      | Ana Dashboard     | Authenticated |
| `/profil`         | Profil Sayfası    | Authenticated |
| `/student/*`      | Öğrenci Sayfaları | STUDENT       |
| `/egitmen/*`      | Eğitmen Sayfaları | INSTRUCTOR    |
| `/yonetim/*`      | Yönetici Sayfaları| TENANT_ADMIN  |
| `/admin/*`        | Süper Admin       | SUPER_ADMIN   |
| `/egitim/oynatici/:courseId`          | Kurs Oynatıcı | Authenticated |
| `/egitmen/canli-yayin/:sessionId`     | Canlı Yayın   | INSTRUCTOR    |

---

## 📝 Boş Modüller (Gelecek Geliştirmeler)

| Modül             | Olası Amaç            |
|-------            |-----------            |
| **BELGENET**      | Belge yönetim sistemi |
| **MUSTERI**       | Müşteri ilişkileri yönetimi (CRM) |
| **SOZLESME**      | Sözleşme yönetim sistemi |

---

## 🔄 Kalıtım Mekanizması

AKADEMI projesi, MAYSCON'dan settings'i şu şekilde kalıtım alır:

```python
# akademi/settings.py

# MAYSCON.V1 PATH CONFIGURATION
MAYSCON_V1_PATH = BASE_DIR.parent / 'MAYSCON' / 'mayscon.v1'
sys.path.insert(0, str(MAYSCON_V1_PATH))

# TÜM AYARLARI MAYSCON'DAN AL
from config.settings import *

# AKADEMI-SPECIFIC OVERRIDES
ROOT_URLCONF = 'akademi.urls'
WSGI_APPLICATION = 'akademi.wsgi.application'
ASGI_APPLICATION = 'akademi.asgi.application'

# Admin panel başlıkları
ADMIN_SITE_HEADER = "Akademi Yönetim Paneli"
ADMIN_SITE_TITLE = "Akademi Admin"
```

---

## ✅ Güçlü Yönler

1. **Modüler Mimari:**      Settings 16 dosyaya ayrılmış, bakımı kolay
2. **Kalıtım Sistemi:**     Yeni projeler merkezi framework'ten faydalanabilir
3. **DevOps Hazır:**        Docker, K8s, Nginx, Gunicorn hazır
4. **Multi-Tenancy:**       Her kurum kendi kimliğine sahip olabilir
5. **SOLID Prensipleri:**   Frontend Clean Code standartlarına uygun
6. **Lazy Loading:**        React.lazy ile performans optimizasyonu
7. **Type Safety:**         TypeScript ile tip güvenliği
8. **Kapsamlı Monitoring:** Terminal ve web dashboard

## ⚠️ Geliştirme Önerileri

1. **Backend Apps Eksik:** `akademi.backend` dizini boş, Django app'leri oluşturulmalı
2. **API Entegrasyonu:**    Frontend şu anda mock data kullanıyor, gerçek API gerekli
3. **Test Eksikliği:**      Frontend testleri görünmüyor
4. **CI/CD:**               GitHub Actions veya GitLab CI eklenebilir
5. **Dokümantasyon:**       API dokümantasyonu (Swagger/OpenAPI) eklenebilir
6. **Tailwind Config:**     Özel Tailwind konfigürasyonu eksik görünüyor

---

## 📊 Dosya İstatistikleri

| Modül                     | Durum         | Dosya Sayısı (Yaklaşık)   |
|-------                    |-------        |------------------------   |
| MAYSCON/mayscon.v1        | ✅ Aktif      | ~100+                     |
| AKADEMI/akademi           | ✅ Aktif      | 5                         |
| AKADEMI/akademi.frontend  | ✅ Aktif      | ~60+                      |
| AKADEMI/akademi.backend   | 📝 Boş | 0 |
| BELGENET                  | 📝 Boş | 0 |
| MUSTERI                   | 📝 Boş | 0 |
| SOZLESME                  | 📝 Boş | 0 |

---

## 🚀 Başlangıç Kılavuzu

### MAYSCON (Backend)

```bash
cd v0/MAYSCON/mayscon.v1

# Virtual environment oluştur
python -m venv .venv
source .venv/bin/activate

# Bağımlılıkları yükle
pip install -r tools/requirements/dev.txt

# Docker ile başlat
make dev

# Veya yerel olarak
make run
```

### AKADEMI Frontend

```bash
cd v0/AKADEMI/akademi.frontend

# Bağımlılıkları yükle
npm install

# Geliştirme sunucusu
npm run dev

# Build
npm run build
```

---

## 📞 İletişim

- **Organizasyon:** Asrın Global
- **E-posta:** dev@asringlobal.com
- **Proje:** BelgeNet

---

*Bu rapor otomatik olarak proje analizi sonucunda oluşturulmuştur.*

