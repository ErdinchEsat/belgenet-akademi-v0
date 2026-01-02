# 🚀 Performance Optimizasyonu - Detaylı Uygulama Planı

> **Modül:** M16.7 - Performance Optimization  
> **Öncelik:** Yüksek  
> **Tahmini Süre:** 3-4 Hafta  
> **Son Güncelleme:** 2 Ocak 2026

---

## 📊 Genel Bakış

Bu döküman, BelgeNet platformunun backend ve frontend performans optimizasyonu için kapsamlı bir uygulama planı sunar. Her bölüm, ölçülebilir hedefler, uygulama adımları ve doğrulama kriterleri içerir.

### Hedef Metrikler

| Metrik | Mevcut | Hedef | Ölçüm Aracı |
|--------|--------|-------|-------------|
| API Response Time (p95) | ~500ms | <200ms | Django Debug Toolbar, New Relic |
| Database Query Count/Request | ~15-30 | <10 | django-silk, pgBadger |
| Frontend Bundle Size | ~2MB | <500KB | webpack-bundle-analyzer |
| Time to First Contentful Paint | ~3s | <1.5s | Lighthouse, WebPageTest |
| Time to Interactive | ~5s | <3s | Lighthouse |
| Memory Usage (Backend) | - | Baseline | memory_profiler |

---

## 1️⃣ Database Query Optimizasyonu

> **Tahmini Süre:** 1 Hafta  
> **Öncelik:** Kritik  
> **Konum:** `v0/AKADEMI/backend/`

### 1.1 Query Profiling Altyapısı

- [x] **django-silk kurulumu ve konfigürasyonu** ✅ (2 Ocak 2026)
  ```bash
  pip install django-silk
  ```
  - [x] `INSTALLED_APPS`'e `silk` ekle → `apps.py`
  - [x] `MIDDLEWARE`'e `silk.middleware.SilkyMiddleware` ekle → `middleware.py`
  - [x] `urls.py`'a `path('silk/', include('silk.urls'))` ekle → `akademi/urls.py`
  - [x] `SILKY_PYTHON_PROFILER = True` ayarla → `profiling.py`
  - [x] Production'da devre dışı bırakma koşulu ekle → DEBUG check

- [ ] **pgBadger log analizi kurulumu**
  ```bash
  # PostgreSQL log ayarları
  log_min_duration_statement = 100  # 100ms üzeri sorguları logla
  log_statement = 'all'
  log_duration = on
  ```
  - [ ] pgBadger kurulumu
  - [ ] Günlük rapor oluşturma cron job'ı
  - [ ] Slow query alert mekanizması

- [x] **Django Debug Toolbar (Development)** ✅ (Önceden kurulu)
  - [x] Sadece DEBUG=True modunda aktif
  - [x] SQL panel aktif
  - [x] Template panel aktif

### 1.2 N+1 Query Analizi ve Düzeltme

- [x] **Kritik API Endpoint'leri İnceleme** ✅ (2 Ocak 2026)
  
  | Endpoint | Beklenen Query | Konum | Durum |
  |----------|----------------|-------|-------|
  | `/api/v1/courses/` | 3-5 | `courses/views.py` | ✅ Zaten optimize |
  | `/api/v1/enrollments/` | 3-5 | `courses/views.py` | ✅ Optimize edildi |
  | `/api/v1/student/classes/` | 3-4 | `student/views.py` | ✅ Optimize edildi |
  | `/api/v1/student/assignments/` | 4-5 | `student/views.py` | ✅ Optimize edildi |
  | `/api/v1/student/live-sessions/` | 3-4 | `student/views.py` | ✅ Optimize edildi |
  | `/api/v1/instructor/dashboard/` | 5-7 | `instructor/views.py` | ✅ Optimize edildi |
  | `/api/v1/instructor/classes/` | 4-6 | `instructor/views.py` | ✅ Optimize edildi |
  | `/api/v1/instructor/students/` | 4-6 | `instructor/views.py` | ✅ Optimize edildi |

- [x] **select_related() Optimizasyonları** ✅ (2 Ocak 2026)
  ```python
  # ÖNCE (N+1)
  courses = Course.objects.all()
  for course in courses:
      print(course.instructor.name)  # Her iterasyonda yeni query
  
  # SONRA (Tek query)
  courses = Course.objects.select_related('instructor', 'tenant').all()
  ```
  
  - [x] `Enrollment.objects` → `user`, `course`, `course__tenant`
  - [x] `ClassGroup.objects` → `course`, `course__tenant`
  - [x] `Assignment.objects` → `class_group`, `class_group__course`, `created_by`
  - [x] `LiveSession.objects` → `class_group`, `class_group__course`, `instructor`

- [x] **prefetch_related() Optimizasyonları** ✅ (2 Ocak 2026)
  ```python
  # ÖNCE (N+1)
  courses = Course.objects.all()
  for course in courses:
      for module in course.modules.all():  # Her kurs için yeni query
          pass
  
  # SONRA (2 query toplam)
  courses = Course.objects.prefetch_related('modules', 'modules__contents').all()
  ```
  
  - [x] `Enrollment` → `course__instructors`, `course__modules`, `content_progress`
  - [x] `ClassGroup` → `instructors`, `live_sessions`, `assignments`, `class_enrollments`
  - [x] `Assignment` → `submissions`

- [x] **Annotate optimizasyonları** ✅ (2 Ocak 2026)
  - [x] `InstructorClassViewSet.list` → `student_count` annotate ile
  - [x] `InstructorStudentViewSet.list` → `enrolled_courses_count`, `avg_score` annotate ile
  - [x] `values_list('id', flat=True)` ile subquery optimizasyonu

### 1.3 Database Index Optimizasyonu

- [ ] **Eksik Index Analizi**
  ```sql
  -- Unused index'leri bul
  SELECT schemaname, relname, indexrelname, idx_scan
  FROM pg_stat_user_indexes
  WHERE idx_scan = 0;
  
  -- Missing index önerileri
  SELECT * FROM pg_stat_user_tables
  WHERE seq_scan > idx_scan AND n_live_tup > 10000;
  ```

- [ ] **Önerilen Index'ler**
  ```python
  # courses/models.py
  class Course(models.Model):
      class Meta:
          indexes = [
              models.Index(fields=['tenant', 'status']),
              models.Index(fields=['category', 'level']),
              models.Index(fields=['created_at']),
              models.Index(fields=['instructor', 'status']),
          ]
  
  # enrollments/models.py
  class Enrollment(models.Model):
      class Meta:
          indexes = [
              models.Index(fields=['user', 'course']),
              models.Index(fields=['course', 'is_completed']),
              models.Index(fields=['enrolled_at']),
          ]
  
  # progress/models.py
  class Progress(models.Model):
      class Meta:
          indexes = [
              models.Index(fields=['user', 'content']),
              models.Index(fields=['updated_at']),
          ]
  ```

- [ ] **Composite Index Stratejisi**
  - [ ] Sık kullanılan WHERE + ORDER BY kombinasyonları
  - [ ] Tenant-based filtering için covering index
  - [ ] Full-text search için GIN index (arama özelliği varsa)

### 1.4 Query Optimization Techniques

- [ ] **only() ve defer() kullanımı**
  ```python
  # Sadece gerekli alanları çek
  courses = Course.objects.only('id', 'title', 'cover_image', 'status')
  
  # Büyük alanları ertele
  courses = Course.objects.defer('description', 'syllabus')
  ```

- [ ] **values() ve values_list() kullanımı**
  ```python
  # ORM object yerine dictionary
  course_ids = Course.objects.filter(status='published').values_list('id', flat=True)
  ```

- [ ] **Aggregate ve Annotate optimizasyonu**
  ```python
  from django.db.models import Count, Avg, Sum
  
  # Tek query'de istatistikler
  stats = Course.objects.aggregate(
      total=Count('id'),
      avg_rating=Avg('average_rating'),
      total_enrollments=Sum('enrollment_count')
  )
  ```

- [ ] **Subquery optimizasyonu**
  ```python
  from django.db.models import Subquery, OuterRef
  
  # Correlated subquery yerine window function
  latest_progress = Progress.objects.filter(
      user=OuterRef('user'),
      content__module__course=OuterRef('course')
  ).order_by('-updated_at')
  
  enrollments = Enrollment.objects.annotate(
      last_activity=Subquery(latest_progress.values('updated_at')[:1])
  )
  ```

### 1.5 Connection Pooling

- [ ] **pgBouncer kurulumu**
  ```yaml
  # docker-compose.yml
  pgbouncer:
    image: edoburu/pgbouncer
    environment:
      DATABASE_URL: postgres://user:pass@db:5432/akademi
      POOL_MODE: transaction
      MAX_CLIENT_CONN: 100
      DEFAULT_POOL_SIZE: 20
  ```

- [ ] **Django settings güncelleme**
  ```python
  DATABASES = {
      'default': {
          'ENGINE': 'django.db.backends.postgresql',
          'HOST': 'pgbouncer',  # Direct DB yerine pgbouncer
          'PORT': 6432,
          'CONN_MAX_AGE': 60,  # Connection reuse
          'OPTIONS': {
              'connect_timeout': 10,
          }
      }
  }
  ```

---

## 2️⃣ Redis Cache Entegrasyonu ✅ TAMAMLANDI (2 Ocak 2026)

> **Tahmini Süre:** 4-5 Gün → **1 Gün**  
> **Öncelik:** Yüksek  
> **Konum:** `v0/AKADEMI/backend/libs/cache/`

### 2.1 Redis Altyapı Kurulumu

- [x] **Cache utility modülleri oluşturuldu** ✅
  - [x] `libs/cache/__init__.py`
  - [x] `libs/cache/decorators.py` - `cache_per_tenant`, `cache_response`, `invalidate_cache_patterns`
  - [x] `libs/cache/managers.py` - `CachedManager`, `TenantCachedManager`
  - [x] `libs/cache/signals.py` - Auto cache invalidation

- [x] **Redis paketleri zaten mevcut** (data.txt)
  - `django-redis>=5.4.0`
  - `redis>=5.0.0`
  - `hiredis>=2.3.0`

- [ ] **Docker Compose güncelleme** (Opsiyonel)
  ```yaml
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3
  ```

- [ ] **Django cache backend konfigürasyonu**
  ```python
  # settings/cache.py
  CACHES = {
      'default': {
          'BACKEND': 'django_redis.cache.RedisCache',
          'LOCATION': 'redis://redis:6379/1',
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
              'SOCKET_CONNECT_TIMEOUT': 5,
              'SOCKET_TIMEOUT': 5,
              'RETRY_ON_TIMEOUT': True,
              'MAX_CONNECTIONS': 50,
              'CONNECTION_POOL_KWARGS': {'max_connections': 50},
              'SERIALIZER': 'django_redis.serializers.json.JSONSerializer',
          },
          'KEY_PREFIX': 'akademi',
          'TIMEOUT': 300,  # 5 dakika default TTL
      },
      'sessions': {
          'BACKEND': 'django_redis.cache.RedisCache',
          'LOCATION': 'redis://redis:6379/2',
          'OPTIONS': {
              'CLIENT_CLASS': 'django_redis.client.DefaultClient',
          },
          'KEY_PREFIX': 'session',
          'TIMEOUT': 86400,  # 24 saat
      }
  }
  
  # Session backend
  SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
  SESSION_CACHE_ALIAS = 'sessions'
  ```

### 2.2 Cache Stratejisi

- [ ] **Cache Layer Tanımları**
  
  | Layer | TTL | Kullanım | Invalidation |
  |-------|-----|----------|--------------|
  | L1 - Request | Request süresi | QuerySet cache | Otomatik |
  | L2 - Short | 5 dakika | API responses | Event-based |
  | L3 - Medium | 1 saat | Aggregations | Schedule |
  | L4 - Long | 24 saat | Config, static | Manual |

- [ ] **Cache key naming convention**
  ```python
  # Format: {prefix}:{resource}:{tenant}:{identifier}:{version}
  # Örnekler:
  # akademi:course:tenant1:123:v1
  # akademi:user:tenant1:456:profile:v1
  # akademi:stats:tenant1:dashboard:v1
  
  def make_cache_key(resource, identifier, tenant_id=None, version='v1'):
      parts = ['akademi', resource]
      if tenant_id:
          parts.append(f't{tenant_id}')
      parts.extend([str(identifier), version])
      return ':'.join(parts)
  ```

### 2.3 View-Level Caching

- [ ] **cache_page decorator**
  ```python
  from django.views.decorators.cache import cache_page
  from django.utils.decorators import method_decorator
  
  class CourseListView(generics.ListAPIView):
      @method_decorator(cache_page(60 * 5))  # 5 dakika
      def get(self, request, *args, **kwargs):
          return super().get(request, *args, **kwargs)
  ```

- [ ] **Conditional caching (tenant-aware)**
  ```python
  from functools import wraps
  from django.core.cache import cache
  
  def cache_per_tenant(timeout=300, key_prefix='view'):
      def decorator(view_func):
          @wraps(view_func)
          def wrapper(request, *args, **kwargs):
              tenant_id = getattr(request, 'tenant', {}).get('id', 'default')
              cache_key = f"{key_prefix}:{tenant_id}:{request.path}:{request.GET.urlencode()}"
              
              response = cache.get(cache_key)
              if response is None:
                  response = view_func(request, *args, **kwargs)
                  cache.set(cache_key, response, timeout)
              return response
          return wrapper
      return decorator
  ```

### 2.4 Model-Level Caching

- [ ] **Cached model manager**
  ```python
  # libs/cache/managers.py
  from django.core.cache import cache
  from django.db import models
  
  class CachedManager(models.Manager):
      cache_timeout = 300
      
      def get_cached(self, pk):
          cache_key = f"{self.model._meta.label}:{pk}"
          instance = cache.get(cache_key)
          if instance is None:
              instance = self.get(pk=pk)
              cache.set(cache_key, instance, self.cache_timeout)
          return instance
      
      def invalidate_cache(self, pk):
          cache_key = f"{self.model._meta.label}:{pk}"
          cache.delete(cache_key)
  ```

- [ ] **Signal-based cache invalidation**
  ```python
  # libs/cache/signals.py
  from django.db.models.signals import post_save, post_delete
  from django.dispatch import receiver
  from django.core.cache import cache
  
  @receiver([post_save, post_delete])
  def invalidate_model_cache(sender, instance, **kwargs):
      if hasattr(instance, 'get_cache_keys'):
          for key in instance.get_cache_keys():
              cache.delete(key)
  ```

### 2.5 API Response Caching

- [ ] **DRF caching middleware**
  ```python
  # libs/cache/middleware.py
  from rest_framework.response import Response
  from django.core.cache import cache
  import hashlib
  
  class APICacheMiddleware:
      CACHE_METHODS = ['GET', 'HEAD']
      DEFAULT_TIMEOUT = 300
      
      def __init__(self, get_response):
          self.get_response = get_response
      
      def __call__(self, request):
          if request.method not in self.CACHE_METHODS:
              return self.get_response(request)
          
          if not request.path.startswith('/api/'):
              return self.get_response(request)
          
          cache_key = self._make_key(request)
          cached = cache.get(cache_key)
          
          if cached:
              return cached
          
          response = self.get_response(request)
          
          if response.status_code == 200:
              cache.set(cache_key, response, self.DEFAULT_TIMEOUT)
          
          return response
      
      def _make_key(self, request):
          user_id = getattr(request.user, 'id', 'anon')
          tenant_id = getattr(request, 'tenant', {}).get('id', 'default')
          path_hash = hashlib.md5(
              f"{request.path}:{request.GET.urlencode()}".encode()
          ).hexdigest()[:12]
          return f"api:resp:{tenant_id}:{user_id}:{path_hash}"
  ```

### 2.6 Cache Monitoring

- [ ] **Redis monitoring setup**
  ```python
  # management/commands/cache_stats.py
  from django.core.management.base import BaseCommand
  from django_redis import get_redis_connection
  
  class Command(BaseCommand):
      def handle(self, *args, **kwargs):
          redis = get_redis_connection("default")
          info = redis.info()
          
          self.stdout.write(f"Used Memory: {info['used_memory_human']}")
          self.stdout.write(f"Connected Clients: {info['connected_clients']}")
          self.stdout.write(f"Keys: {redis.dbsize()}")
          self.stdout.write(f"Hit Rate: {info.get('keyspace_hits', 0) / (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1)) * 100:.2f}%")
  ```

---

## 3️⃣ API Response Compression ✅ TAMAMLANDI (2 Ocak 2026)

> **Tahmini Süre:** 1 Gün → **10 Dakika**  
> **Öncelik:** Orta  
> **Konum:** `v0/MAYSCON/mayscon.v1/config/settings/middleware.py`

### 3.1 Django GZip Middleware

- [x] **Middleware ekleme** ✅
  ```python
  # middleware.py - build_middleware() fonksiyonunda
  middleware.append('django.middleware.gzip.GZipMiddleware')  # En üste eklendi
  ```

- [x] **Compression paketleri zaten mevcut** (prod.txt)
  - `whitenoise>=6.6.0`
  - `brotli>=1.1.0`

### 3.2 Nginx Compression

- [ ] **nginx.conf güncelleme**
  ```nginx
  http {
      # Gzip Settings
      gzip on;
      gzip_vary on;
      gzip_proxied any;
      gzip_comp_level 6;
      gzip_buffers 16 8k;
      gzip_http_version 1.1;
      gzip_min_length 256;
      gzip_types
          application/atom+xml
          application/geo+json
          application/javascript
          application/json
          application/ld+json
          application/manifest+json
          application/rdf+xml
          application/rss+xml
          application/xhtml+xml
          application/xml
          font/eot
          font/otf
          font/ttf
          image/svg+xml
          text/css
          text/javascript
          text/plain
          text/xml;
      
      # Brotli (daha iyi sıkıştırma)
      brotli on;
      brotli_comp_level 6;
      brotli_types application/json application/javascript text/css text/plain;
  }
  ```

### 3.3 Response Size Optimization

- [ ] **Pagination zorunluluğu**
  ```python
  # settings/rest_framework.py
  REST_FRAMEWORK = {
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 20,
      'MAX_PAGE_SIZE': 100,
  }
  ```

- [ ] **Field selection (sparse fieldsets)**
  ```python
  # views.py
  class CourseViewSet(viewsets.ModelViewSet):
      def get_serializer(self, *args, **kwargs):
          fields = self.request.query_params.get('fields')
          if fields:
              kwargs['fields'] = fields.split(',')
          return super().get_serializer(*args, **kwargs)
  
  # serializers.py
  class DynamicFieldsSerializer(serializers.ModelSerializer):
      def __init__(self, *args, **kwargs):
          fields = kwargs.pop('fields', None)
          super().__init__(*args, **kwargs)
          if fields:
              allowed = set(fields)
              existing = set(self.fields)
              for field_name in existing - allowed:
                  self.fields.pop(field_name)
  ```

---

## 4️⃣ Frontend Code Splitting ✅ TAMAMLANDI (2 Ocak 2026)

> **Tahmini Süre:** 3-4 Gün → **30 Dakika**  
> **Öncelik:** Yüksek  
> **Konum:** `v0/AKADEMI/frontend/vite.config.ts`

### 4.1 Route-Based Code Splitting

- [x] **React.lazy() implementasyonu** ✅ (Zaten mevcut - 35+ sayfa)

- [x] **Vite manualChunks konfigürasyonu** ✅
  ```typescript
  manualChunks: {
    'vendor-react': ['react', 'react-dom', 'react-router-dom'],
    'vendor-charts': ['recharts'],
    'vendor-video': ['video.js'],
    'vendor-icons': ['lucide-react'],
    'vendor-utils': ['axios', 'clsx', 'tailwind-merge', 'jwt-decode'],
  }
  ```

- [x] **Build optimizasyonları** ✅
  - `chunkSizeWarningLimit: 500`
  - `sourcemap: false`, `minify: 'esbuild'`, `target: 'es2020'`

### 4.2 Component-Level Splitting (Önceden Yapılmış)

- [x] **Heavy components lazy loading** ✅
  ```typescript
  // App.tsx
  import { lazy, Suspense } from 'react';
  
  // Lazy loaded components
  const Dashboard = lazy(() => import('./features/lms/pages/Dashboard'));
  const CoursePlayer = lazy(() => import('./features/lms/pages/CoursePlayer'));
  const AdminPanel = lazy(() => import('./features/admin/pages/AdminDashboard'));
  const Profile = lazy(() => import('./features/core/pages/ProfilePage'));
  
  // Loading fallback
  const PageLoader = () => (
    <div className="flex items-center justify-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  );
  
  function App() {
    return (
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/dashboard/*" element={<Dashboard />} />
          <Route path="/course/:id" element={<CoursePlayer />} />
          <Route path="/admin/*" element={<AdminPanel />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </Suspense>
    );
  }
  ```

- [ ] **Named chunks için Vite magic comments**
  ```typescript
  const Dashboard = lazy(() => 
    import(/* webpackChunkName: "dashboard" */ './features/lms/pages/Dashboard')
  );
  ```

### 4.2 Component-Level Splitting

- [ ] **Heavy components lazy loading**
  ```typescript
  // Ağır kütüphaneler içeren componentler
  const VideoPlayer = lazy(() => import('./components/player/VideoPlayer'));
  const RichTextEditor = lazy(() => import('./components/editor/RichTextEditor'));
  const ChartDashboard = lazy(() => import('./components/charts/ChartDashboard'));
  const CalendarWidget = lazy(() => import('./components/calendar/CalendarWidget'));
  ```

- [ ] **Conditional loading**
  ```typescript
  // Sadece gerektiğinde yükle
  const AdminTools = lazy(() => {
    if (user?.role === 'ADMIN') {
      return import('./features/admin/components/AdminTools');
    }
    return Promise.resolve({ default: () => null });
  });
  ```

### 4.3 Vendor Chunk Optimization

- [ ] **Vite config güncelleme**
  ```typescript
  // vite.config.ts
  import { defineConfig } from 'vite';
  
  export default defineConfig({
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            // React core
            'vendor-react': ['react', 'react-dom', 'react-router-dom'],
            // UI framework
            'vendor-ui': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
            // Charts (büyük)
            'vendor-charts': ['recharts', 'd3'],
            // Video player
            'vendor-video': ['video.js', 'hls.js'],
            // Utilities
            'vendor-utils': ['lodash-es', 'date-fns', 'axios'],
          },
        },
      },
      chunkSizeWarningLimit: 500,
    },
  });
  ```

### 4.4 Dynamic Imports for Heavy Libraries

- [ ] **On-demand library loading**
  ```typescript
  // Sadece PDF export gerektiğinde yükle
  const exportToPDF = async (data: ReportData) => {
    const { jsPDF } = await import('jspdf');
    const doc = new jsPDF();
    // ...
  };
  
  // Sadece Excel export gerektiğinde yükle
  const exportToExcel = async (data: any[]) => {
    const XLSX = await import('xlsx');
    const worksheet = XLSX.utils.json_to_sheet(data);
    // ...
  };
  ```

---

## 5️⃣ Image Lazy Loading

> **Tahmini Süre:** 2 Gün  
> **Öncelik:** Orta  
> **Konum:** `v0/AKADEMI/frontend/components/`

### 5.1 Native Lazy Loading

- [ ] **Image component güncelleme**
  ```tsx
  // components/ui/LazyImage.tsx
  interface LazyImageProps {
    src: string;
    alt: string;
    className?: string;
    placeholder?: string;
    onLoad?: () => void;
  }
  
  export const LazyImage: React.FC<LazyImageProps> = ({
    src,
    alt,
    className,
    placeholder = '/placeholder.svg',
    onLoad,
  }) => {
    const [isLoaded, setIsLoaded] = useState(false);
    const [error, setError] = useState(false);
  
    return (
      <div className={cn('relative overflow-hidden', className)}>
        {!isLoaded && (
          <div className="absolute inset-0 bg-slate-200 animate-pulse" />
        )}
        <img
          src={error ? placeholder : src}
          alt={alt}
          loading="lazy"
          decoding="async"
          className={cn(
            'transition-opacity duration-300',
            isLoaded ? 'opacity-100' : 'opacity-0'
          )}
          onLoad={() => {
            setIsLoaded(true);
            onLoad?.();
          }}
          onError={() => setError(true)}
        />
      </div>
    );
  };
  ```

### 5.2 Intersection Observer Implementation

- [ ] **useIntersectionObserver hook**
  ```typescript
  // hooks/useIntersectionObserver.ts
  export function useIntersectionObserver(
    ref: RefObject<Element>,
    options: IntersectionObserverInit = {}
  ): boolean {
    const [isIntersecting, setIsIntersecting] = useState(false);
  
    useEffect(() => {
      const element = ref.current;
      if (!element) return;
  
      const observer = new IntersectionObserver(
        ([entry]) => {
          if (entry.isIntersecting) {
            setIsIntersecting(true);
            observer.disconnect(); // Bir kez yüklenince dur
          }
        },
        { rootMargin: '100px', threshold: 0.1, ...options }
      );
  
      observer.observe(element);
      return () => observer.disconnect();
    }, [ref, options]);
  
    return isIntersecting;
  }
  ```

- [ ] **LazyImage with Intersection Observer**
  ```tsx
  export const LazyImage: React.FC<LazyImageProps> = ({ src, alt, ...props }) => {
    const ref = useRef<HTMLDivElement>(null);
    const isVisible = useIntersectionObserver(ref);
    const [imageSrc, setImageSrc] = useState<string | null>(null);
  
    useEffect(() => {
      if (isVisible) {
        setImageSrc(src);
      }
    }, [isVisible, src]);
  
    return (
      <div ref={ref}>
        {imageSrc ? (
          <img src={imageSrc} alt={alt} {...props} />
        ) : (
          <div className="bg-slate-200 animate-pulse" style={props.style} />
        )}
      </div>
    );
  };
  ```

### 5.3 Image Optimization

- [ ] **Responsive images**
  ```tsx
  <picture>
    <source
      media="(max-width: 640px)"
      srcSet={`${baseUrl}?w=320 1x, ${baseUrl}?w=640 2x`}
    />
    <source
      media="(max-width: 1024px)"
      srcSet={`${baseUrl}?w=640 1x, ${baseUrl}?w=1280 2x`}
    />
    <img
      src={`${baseUrl}?w=1280`}
      alt={alt}
      loading="lazy"
    />
  </picture>
  ```

- [ ] **WebP/AVIF format desteği**
  ```tsx
  <picture>
    <source type="image/avif" srcSet={`${baseUrl}.avif`} />
    <source type="image/webp" srcSet={`${baseUrl}.webp`} />
    <img src={`${baseUrl}.jpg`} alt={alt} loading="lazy" />
  </picture>
  ```

- [ ] **CDN entegrasyonu (opsiyonel)**
  ```typescript
  // lib/image.ts
  export function getImageUrl(path: string, options: ImageOptions = {}): string {
    const { width = 800, quality = 80, format = 'webp' } = options;
    const cdnBase = import.meta.env.VITE_CDN_URL || '';
    return `${cdnBase}${path}?w=${width}&q=${quality}&fmt=${format}`;
  }
  ```

---

## 6️⃣ Bundle Size Analizi

> **Tahmini Süre:** 1-2 Gün  
> **Öncelik:** Orta  
> **Konum:** `v0/AKADEMI/frontend/`

### 6.1 Bundle Analyzer Kurulumu

- [ ] **rollup-plugin-visualizer kurulumu**
  ```bash
  npm install -D rollup-plugin-visualizer
  ```

- [ ] **Vite config güncelleme**
  ```typescript
  // vite.config.ts
  import { visualizer } from 'rollup-plugin-visualizer';
  
  export default defineConfig({
    plugins: [
      react(),
      visualizer({
        filename: 'bundle-stats.html',
        open: true,
        gzipSize: true,
        brotliSize: true,
      }),
    ],
  });
  ```

### 6.2 Dependency Audit

- [ ] **Gereksiz dependency'leri tespit**
  ```bash
  # Kullanılmayan paketleri bul
  npx depcheck
  
  # Paket boyutlarını kontrol
  npx cost-of-modules
  ```

- [ ] **Büyük paketleri tespit ve değerlendirme**
  
  | Paket | Boyut | Alternatif | Aksiyon |
  |-------|-------|------------|---------|
  | moment.js | ~300KB | date-fns (~30KB) | Değiştir |
  | lodash | ~70KB | lodash-es (tree-shake) | Güncelle |
  | chart.js | ~200KB | recharts | Değerlendir |
  | axios | ~15KB | native fetch | Değerlendir |

- [ ] **Tree-shakeable import'lar**
  ```typescript
  // ❌ Tüm kütüphaneyi import etme
  import _ from 'lodash';
  
  // ✅ Sadece kullanılanı import et
  import { debounce, throttle } from 'lodash-es';
  
  // ❌ Tüm icons
  import * as Icons from 'lucide-react';
  
  // ✅ Sadece kullanılanlar
  import { User, Settings, Home } from 'lucide-react';
  ```

### 6.3 Performance Budget

- [ ] **Budget tanımlama**
  ```typescript
  // vite.config.ts
  export default defineConfig({
    build: {
      rollupOptions: {
        output: {
          // Her chunk max 200KB
          experimentalMinChunkSize: 10000,
        },
      },
    },
  });
  ```

- [ ] **CI/CD bundle check**
  ```yaml
  # .github/workflows/bundle-check.yml
  - name: Build and analyze
    run: npm run build
    
  - name: Check bundle size
    run: |
      MAX_SIZE=500000  # 500KB
      BUNDLE_SIZE=$(stat -f%z dist/assets/*.js | awk '{sum+=$1} END {print sum}')
      if [ $BUNDLE_SIZE -gt $MAX_SIZE ]; then
        echo "Bundle size ($BUNDLE_SIZE) exceeds limit ($MAX_SIZE)"
        exit 1
      fi
  ```

---

## 📋 Uygulama Kontrol Listesi

### Hafta 1: Database & Query Optimization
- [ ] django-silk kurulumu ve profiling başlangıcı
- [ ] Top 10 yavaş endpoint tespit
- [ ] select_related/prefetch_related implementasyonu
- [ ] Index analizi ve ekleme
- [ ] Connection pooling kurulumu

### Hafta 2: Caching Layer
- [ ] Redis kurulumu ve konfigürasyonu
- [ ] View-level caching implementasyonu
- [ ] Model-level caching implementasyonu
- [ ] Cache invalidation stratejisi
- [ ] Monitoring setup

### Hafta 3: API & Response Optimization
- [ ] Compression middleware aktifleştirme
- [ ] Nginx gzip/brotli konfigürasyonu
- [ ] Pagination zorunluluğu
- [ ] Response size optimizasyonu

### Hafta 4: Frontend Optimization
- [ ] Code splitting implementasyonu
- [ ] Lazy loading komponentler
- [ ] Image lazy loading
- [ ] Bundle analizi ve küçültme
- [ ] Performance budget tanımlama

---

## 📊 Başarı Kriterleri

| Metrik | Mevcut | Hedef | Kabul Kriteri |
|--------|--------|-------|---------------|
| API p95 Latency | 500ms | <200ms | ✅ 60% iyileşme |
| Query/Request | 20 | <10 | ✅ 50% azalma |
| Bundle Size | 2MB | <500KB | ✅ 75% azalma |
| LCP | 3s | <1.5s | ✅ 50% iyileşme |
| Cache Hit Rate | 0% | >80% | ✅ |

---

> 📌 **Not:** Her optimizasyon öncesi ve sonrası benchmark alınmalıdır.  
> 📌 **Öneri:** Production'a almadan önce staging ortamında load testing yapılmalıdır.
