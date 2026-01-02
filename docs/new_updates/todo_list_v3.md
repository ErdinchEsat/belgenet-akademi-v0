# 🎯 Backend Test Stabilizasyonu - Detaylı Todo List v3

> **Başlangıç Tarihi:** 29 Aralık 2024  
> **Hedef:** Test pass rate %79 → %90+  
> **Mevcut Durum:** 330 passed, 27 failed, 59 skipped

---

## 📊 Hedef Metrikler

| Aşama | Hedef Pass Rate | Kritik Metrik |
|-------|-----------------|---------------|
| P0 Sonrası | ≥%83 | Permission fail = 0, tenant leak = 0 |
| P1 Sonrası | ≥%90 | API fail = 0 (skip hariç) |
| P2 Sonrası | ≥%95 | Workflow/integration fail = 0 |

---

## 🔴 P0 — Güvenlik ve Yetkilendirme (Bloklayıcı)

### P0.1 Karar Tablosu Oluşturma
- [ ] `docs/new_updates/decision_table.md` dosyası oluştur
- [ ] 27 fail test için satır aç
- [ ] 59 skip test için satır aç
- [ ] Her satır için karar belirle: `Fix Product` / `Fix Test` / `Skip`
- [ ] Her satır için öncelik ata: `P0` / `P1` / `P2` / `P3`
- [ ] Belirsiz satır olmadığını doğrula

**Format:**
```
| Test/Endpoint | Beklenen | Gerçek | Karar | Öncelik | Owner | Not |
```

**Done Criteria:** ✅ Tüm 86 test (27 fail + 59 skip) için karar satırı var

---

### P0.2 DRF Default Permission Güncelleme
- [ ] `v0/AKADEMI/akademi/settings_test.py` dosyasını oku
- [ ] `REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]` kontrol et
- [ ] `IsAuthenticated` default olarak ayarla
- [ ] Anonymous test case'leri güncelle (401 bekle)
- [ ] Permission matrix anon senaryolarını test et

**Kod Değişikliği:**
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    ...
}
```

**Done Criteria:** ✅ Anonymous istekler 401 dönüyor

---

### P0.3 Admin Endpoint Yetkisi
- [ ] `/api/v1/admin/` route'larını listele
- [ ] Admin viewset'leri incele:
  - [ ] `backend/admin_api/views.py`
  - [ ] `backend/admin_api/urls.py`
- [ ] Her viewset için permission_classes kontrol et
- [ ] `IsAdminUser` veya `IsTenantAdmin` ekle
- [ ] Test et: Student → 403, Admin → 200

**Hedef Viewset'ler:**
- [ ] `UserAdminViewSet`
- [ ] `CourseAdminViewSet`
- [ ] `TenantAdminViewSet`
- [ ] `AuditLogViewSet` (varsa)
- [ ] `DashboardViewSet`

**Done Criteria:** ✅ Student/Instructor ile admin endpoint'ler 403

---

### P0.4 Users Endpoint RBAC
- [ ] `/api/v1/users/` viewset'ini incele
- [ ] Mevcut permission_classes kontrol et
- [ ] RBAC kuralları uygula:
  ```python
  # GET /api/v1/users/
  Student/Instructor: 403 veya sadece "me"
  TenantAdmin: tenant içi kullanıcılar
  SuperAdmin: tüm kullanıcılar
  
  # POST /api/v1/users/
  Student/Instructor: 403
  TenantAdmin/SuperAdmin: 201
  ```
- [ ] Custom permission class oluştur (gerekirse)
- [ ] Test et ve permission matrix güncelle

**Done Criteria:** ✅ Permission matrix /api/v1/users/ fail = 0

---

### P0.5 Course Draft Görünürlük Filtresi
- [ ] `backend/courses/views.py` CourseViewSet incele
- [ ] `get_queryset()` metodunu kontrol et
- [ ] Draft filtreleme mantığı ekle:
  ```python
  def get_queryset(self):
      user = self.request.user
      qs = Course.objects.filter(tenant=user.tenant)
      
      if user.role == 'STUDENT':
          return qs.filter(status='published', is_published=True)
      elif user.role == 'INSTRUCTOR':
          return qs.filter(
              Q(status='published') | Q(instructors=user)
          )
      # Admin: tenant içi hepsi
      return qs
  ```
- [ ] Test et: Student draft course görememeli

**Done Criteria:** ✅ Draft course visibility test geçiyor

---

### P0.6 Course Update Owner Kontrolü
- [ ] Course update endpoint'ini incele
- [ ] `IsOwnerOrAdmin` permission class oluştur/kontrol et:
  ```python
  class IsOwnerOrAdmin(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          if request.user.role in ['ADMIN', 'TENANT_ADMIN', 'SUPER_ADMIN']:
              return True
          return request.user in obj.instructors.all()
  ```
- [ ] PATCH/PUT için permission_classes ekle
- [ ] Test et: Non-owner → 403, Owner → 200

**Done Criteria:** ✅ Course update owner test geçiyor

---

### P0.7 Multi-tenant İzolasyon Standardı
- [ ] `docs/new_updates/compatibility_checklist.md` oluştur
- [ ] Cross-tenant erişim kuralını belirle:
  - [ ] **Karar:** 404 mü 403 mü? (Öneri: 404 - bilgi sızdırmama)
- [ ] Tüm viewset'lerde tenant filtering kontrol et
- [ ] `test_multi_tenant.py` güncelle
- [ ] Tutarlılık testi yap

**Kontrol Edilecek Viewset'ler:**
- [ ] UserViewSet
- [ ] CourseViewSet
- [ ] EnrollmentViewSet
- [ ] Diğer resource viewset'ler

**Done Criteria:** ✅ test_multi_tenant.py fail = 0

---

## 🟠 P1 — API Davranış Tutarlılığı

### P1.1 Login Nonexistent Email Status
- [ ] Auth login endpoint'ini incele
- [ ] Mevcut davranışı kontrol et (401 vs 400)
- [ ] **Karar al:**
  - [ ] Option A: 401'e çevir (güvenlik için)
  - [ ] Option B: Test'i 400'e revize et
- [ ] Seçilen yöne göre uygula
- [ ] Hata mesajı "user exists" bilgisi sızdırmıyor mu kontrol et

**Güvenlik Notu:** Farklı email vs yanlış şifre için aynı mesaj

**Done Criteria:** ✅ test_login_nonexistent_email geçiyor

---

### P1.2 Logout Refresh Blacklist
- [ ] SimpleJWT blacklist ayarlarını kontrol et
- [ ] **Karar al:**
  - [ ] Option A: Blacklist implement et
    - [ ] `rest_framework_simplejwt.token_blacklist` ekle
    - [ ] Migration çalıştır
    - [ ] Logout endpoint'te refresh token blacklist et
  - [ ] Option B: Test skip et veya revize et
- [ ] Seçilen yöne göre uygula

**Done Criteria:** ✅ test_logout_blacklists_token stabil

---

### P1.3 API Tutarsızlıkları
- [ ] `instructor_create_course` 403 analizi:
  - [ ] Instructor course oluşturabilmeli mi?
  - [ ] Permission veya test güncelle
- [ ] `cancel_enrollment` 404 analizi:
  - [ ] Endpoint var mı?
  - [ ] Implement et veya test skip et
- [ ] `owner_can_update` analizi
- [ ] `update_only_owner` analizi

**Done Criteria:** ✅ API fail sayısı 0

---

### P1.4 Boş Liste Testleri
- [ ] `list_classes` testini incele
- [ ] Factory/fixture ile test data oluştur:
  - [ ] ClassGroup oluştur
  - [ ] Enrollment mapping yap
- [ ] Veya test beklentisini revize et

**Done Criteria:** ✅ "200 + []" kaynaklı fail yok

---

### P1.5 Validation 400 Düzeltmeleri
- [ ] `create_calendar_event` 400 analizi:
  - [ ] Serializer required fields kontrol et
  - [ ] Test payload'ı düzelt
- [ ] Diğer validation fail'leri dokümante et

**Done Criteria:** ✅ Beklenmeyen 400 yok

---

## 🟡 P2 — Feature Completeness & Skip Yönetimi

### P2.1 Skip Registry Oluşturma
- [ ] `docs/new_updates/skip_registry.md` oluştur
- [ ] 59 skip'i kategorize et:
  - [ ] ENDPOINT_NOT_IMPLEMENTED (35)
  - [ ] FEATURE_NOT_IMPLEMENTED (17)
  - [ ] DB/MIGRATION_ISSUE (7)
- [ ] Her skip için:
  - [ ] Neden
  - [ ] Owner
  - [ ] Hedef sprint

**Done Criteria:** ✅ Her skip kayıtlı ve owner'lı

---

### P2.2 Otomatik Skip Helper
- [ ] `tests/akademi/fixtures/helpers.py` güncelle
- [ ] `route_exists(path, method)` helper ekle:
  ```python
  def route_exists(path: str, method: str = 'GET') -> bool:
      """Check if route exists in URL configuration"""
      from django.urls import resolve, Resolver404
      try:
          resolve(path)
          return True
      except Resolver404:
          return False
  
  def skip_if_no_endpoint(path: str, method: str = 'GET'):
      """Decorator to skip test if endpoint not implemented"""
      def decorator(func):
          @pytest.mark.skipif(
              not route_exists(path, method),
              reason=f"ENDPOINT_NOT_IMPLEMENTED: {method} {path}"
          )
          def wrapper(*args, **kwargs):
              return func(*args, **kwargs)
          return wrapper
      return decorator
  ```

**Done Criteria:** ✅ Branch farklarında testler patlamıyor

---

### P2.3 MVP Eksik Endpoint'ler
MVP kapsamında olması gereken endpoint'ler:
- [ ] `POST /api/v1/enrollments/{id}/cancel/`
- [ ] `POST /api/v1/courses/{slug}/approve/`
- [ ] `GET /api/v1/admin/audit-logs/`
- [ ] `GET /api/v1/certificates/`

Her biri için:
- [ ] Viewset oluştur veya action ekle
- [ ] URL routing ekle
- [ ] Serializer hazırla
- [ ] Test güncelle

**Done Criteria:** ✅ MVP endpoint'ler implement

---

### P2.4 Workflow Test Revizyonu
- [ ] `test_workflow.py` incele
- [ ] Certificate opsiyonel ise:
  - [ ] Feature flag/skip ekle
- [ ] Bulk import/export yoksa:
  - [ ] Skip + GAP kaydı

**Done Criteria:** ✅ Workflow fail = 0 (MVP scope)

---

### P2.5 Bulk Ops Tenant Filtering
- [ ] Bulk/list endpoint'leri incele
- [ ] Queryset tenant filtreleri kontrol et
- [ ] Admin/superadmin istisnaları standardize et
- [ ] `bulk_operations_tenant_scoped` testi düzelt

**Done Criteria:** ✅ Bulk ops tenant scoped test geçiyor

---

## 🟢 P3 — Temizlik ve Performans

### P3.1 MD5 Hasher Test Düzeltmesi
- [ ] `test_password_hashing` testini güncelle:
  ```python
  def test_password_hashing(self, user_a):
      """Password should use configured hash algorithm"""
      from django.conf import settings
      hasher = settings.PASSWORD_HASHERS[0]
      
      if 'MD5' in hasher:
          assert user_a.password.startswith('md5$')
      else:
          assert user_a.password.startswith(
              ('pbkdf2_sha256$', 'argon2$', 'bcrypt$')
          )
  ```

**Done Criteria:** ✅ Test ortama duyarlı çalışıyor

---

### P3.2 N+1 Query Kontrolleri
- [ ] `pytest-django` num_queries fixture kullan
- [ ] Kritik endpoint'lere query limit ekle:
  - [ ] Course list
  - [ ] Dashboard endpoints
  - [ ] User list
- [ ] Query limitleri dokümante et

**Done Criteria:** ✅ N+1 regresyonları yakalanıyor

---

## 📋 İlerleme Takibi

### P0 Durumu
| Task | Durum | Tarih |
|------|-------|-------|
| P0.1 Karar Tablosu | ✅ | 29 Aralık 2024 |
| P0.2 DRF Permission | ✅ | 29 Aralık 2024 |
| P0.3 Admin Yetkisi | ✅ | 29 Aralık 2024 (Belgelendi) |
| P0.4 Users RBAC | ⬜ | - |
| P0.5 Draft Filter | ⬜ | - |
| P0.6 Owner Check | ⬜ | - |
| P0.7 Multi-tenant | ✅ | 29 Aralık 2024 (Belgelendi) |

### P1 Durumu
| Task | Durum | Tarih |
|------|-------|-------|
| P1.1 Login Status | ⬜ | - |
| P1.2 Logout Blacklist | ⬜ | - |
| P1.3 API Tutarsızlık | ⬜ | - |
| P1.4 Boş Liste | ⬜ | - |
| P1.5 Validation | ⬜ | - |

### P2 Durumu
| Task | Durum | Tarih |
|------|-------|-------|
| P2.1 Skip Registry | ✅ | 29 Aralık 2024 |
| P2.2 Skip Helper | ⬜ | - |
| P2.3 MVP Endpoint | ⬜ | - |
| P2.4 Workflow Test | ⬜ | - |
| P2.5 Bulk Tenant | ⬜ | - |

### P3 Durumu
| Task | Durum | Tarih |
|------|-------|-------|
| P3.1 MD5 Test | ⬜ | - |
| P3.2 N+1 Query | ⬜ | - |

---

## 🎯 Execution Order

```
HAFTA 1 (P0 - Güvenlik Kritik)
├── Gün 1: P0.1 Karar Tablosu + P0.2 DRF Permission
├── Gün 2: P0.3 Admin Yetkisi + P0.4 Users RBAC
├── Gün 3: P0.5 Draft Filter + P0.6 Owner Check
└── Gün 4: P0.7 Multi-tenant + P0 Test Validation

HAFTA 2 (P1 - API Tutarlılık)
├── Gün 1: P1.1 Login + P1.2 Logout
├── Gün 2: P1.3 API Tutarsızlıkları
└── Gün 3: P1.4 Boş Liste + P1.5 Validation

HAFTA 3 (P2 - Feature & Skip)
├── Gün 1: P2.1 Skip Registry + P2.2 Helper
├── Gün 2-4: P2.3 MVP Endpoint'ler
└── Gün 5: P2.4 Workflow + P2.5 Bulk

HAFTA 4 (P3 - Temizlik)
├── Gün 1: P3.1 MD5 Test
└── Gün 2: P3.2 N+1 Query
```

---

**Son Güncelleme:** 29 Aralık 2024

