# 🔒 API Uyumluluk ve Güvenlik Kontrol Listesi

> **Tarih:** 29 Aralık 2024  
> **Durum:** P0 Güvenlik Açıkları Tespit Edildi  
> **Kritiklik:** 🔴 YÜKSEK

---

## 🚨 TESPİT EDİLEN GÜVENLİK AÇIKLARI

### 1. Admin Endpoint'ler Tüm Kullanıcılara Açık

**Dosya:** `v0/AKADEMI/backend/admin_api/views.py`

**Sorun:** Tüm admin viewset'ler sadece `IsAuthenticated` kullanıyor. Bu, herhangi bir authenticated user'ın (student dahil) admin işlemleri yapabilmesi anlamına geliyor.

**Etkilenen Endpoint'ler:**

| Endpoint | ViewSet | Mevcut Permission | Olması Gereken |
|----------|---------|-------------------|----------------|
| `/api/v1/admin/dashboard/` | TenantDashboardView | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/users/` | AdminUserViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/courses/` | AdminCourseViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/class-groups/` | AdminClassGroupViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/ops-inbox/` | AdminOpsInboxViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/reports/` | AdminReportsViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/roles/` | AdminRolesViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/tenants/` | AdminTenantsViewSet | IsAuthenticated | IsSuperAdmin |
| `/api/v1/admin/logs/tech/` | TechLogsViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/logs/activity/` | ActivityLogsViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/finance/*` | Finance Views | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/live-sessions/` | GlobalLiveSessionsViewSet | IsAuthenticated | IsAdminOrSuperAdmin |
| `/api/v1/admin/system/stats/` | SystemStatsView | IsAuthenticated | IsSuperAdmin |

---

## 📝 MEVCUT PERMISSION CLASS'LAR

**Dosya:** `v0/AKADEMI/backend/users/permissions.py`

```python
# Rol Bazlı
IsStudent              # role == STUDENT
IsInstructor           # role == INSTRUCTOR
IsTenantAdmin          # role == TENANT_ADMIN
IsSuperAdmin           # role == SUPER_ADMIN

# Kombinasyonlar
IsAdminOrSuperAdmin    # role in [TENANT_ADMIN, SUPER_ADMIN]
IsInstructorOrAdmin    # role in [INSTRUCTOR, TENANT_ADMIN, SUPER_ADMIN]

# Obje Bazlı
IsSameTenant           # obj.tenant == user.tenant
IsOwnerOrAdmin         # obj.user == user OR admin
```

---

## ✅ ÇÖZÜM PLANI

### P0.3: Admin Endpoint Düzeltmesi

**Değişiklik Dosyası:** `v0/AKADEMI/backend/admin_api/views.py`

```python
# ÖNCE (Güvensiz)
class TenantDashboardView(APIView):
    permission_classes = [IsAuthenticated]

# SONRA (Güvenli)
from backend.users.permissions import IsAdminOrSuperAdmin, IsSuperAdmin

class TenantDashboardView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
```

**Tüm Değişiklikler:**

| ViewSet | Satır | Değişiklik |
|---------|-------|------------|
| TenantDashboardView | 86 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminUserViewSet | 413 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminCourseViewSet | 785 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminClassGroupViewSet | 1228 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminOpsInboxViewSet | 1735 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminReportsViewSet | 2114 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminRolesViewSet | 2840 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| AdminTenantsViewSet | 3100 | `[IsAuthenticated]` → `[IsAuthenticated, IsSuperAdmin]` |
| SystemStatsView | 3320 | `[IsAuthenticated]` → `[IsAuthenticated, IsSuperAdmin]` |
| TechLogsViewSet | 3396 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| ActivityLogsViewSet | 3435 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| FinanceAcademiesView | 3486 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| FinanceCategoriesView | 3518 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| FinanceInstructorsView | 3535 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |
| GlobalLiveSessionsViewSet | 3577 | `[IsAuthenticated]` → `[IsAuthenticated, IsAdminOrSuperAdmin]` |

---

## 🔍 P0.4: Users Endpoint RBAC

**Dosya:** `v0/AKADEMI/backend/users/views.py`

**Mevcut Davranış:** Tüm authenticated user'lar `/api/v1/users/` listesini görebiliyor

**Olması Gereken:**
- Student: Sadece kendi profili (`/api/v1/auth/me/`)
- Instructor: Sadece kendi profili
- TenantAdmin: Tenant içi tüm kullanıcılar
- SuperAdmin: Tüm kullanıcılar

**Çözüm:**

```python
class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'SUPER_ADMIN':
            return User.objects.all()
        return User.objects.filter(tenant=user.tenant)
```

---

## 🔍 P0.5: Course Draft Görünürlük

**Dosya:** `v0/AKADEMI/backend/courses/views.py`

**Mevcut Davranış:** Student draft course görebiliyor

**Olması Gereken:**
- Student: Sadece `status='published'` ve `is_published=True`
- Instructor: Kendi draft'ları + published
- Admin: Tenant içi hepsi

**Çözüm:**

```python
class CourseViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.filter(tenant=user.tenant)
        
        if user.role == 'STUDENT':
            return qs.filter(status='published', is_published=True)
        elif user.role == 'INSTRUCTOR':
            return qs.filter(
                Q(status='published', is_published=True) | 
                Q(instructors=user)
            )
        # Admin/SuperAdmin: hepsi
        return qs
```

---

## 🔍 P0.6: Course Update Owner Check

**Dosya:** `v0/AKADEMI/backend/courses/views.py`

**Mevcut Davranış:** Non-owner instructor course update edebiliyor

**Olması Gereken:**
- Owner Instructor: Update edebilir
- Non-owner Instructor: 403
- Admin: Update edebilir

**Çözüm:**

```python
from backend.users.permissions import IsOwnerOrAdmin

class CourseViewSet(viewsets.ModelViewSet):
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        return super().get_permissions()
    
    # IsOwnerOrAdmin için instructor kontrolü
    # views.py'deki has_object_permission'da:
    # Course için: return user in obj.instructors.all() OR admin
```

---

## 🔍 P0.7: Multi-tenant İzolasyon Standardı

### Karar: Cross-tenant erişimde 404 mü 403 mü?

**Öneri:** `404 NOT FOUND`

**Gerekçe:**
1. **Güvenlik:** 403 "kaynak var ama erişemezsin" bilgisi sızdırır
2. **OWASP Önerisi:** Enumeration saldırılarını önlemek için 404
3. **Best Practice:** AWS, Azure, GCP hepsi 404 döner

**Uygulama:**

```python
def get_queryset(self):
    """Tenant-scoped queryset."""
    user = self.request.user
    if user.role == 'SUPER_ADMIN':
        return self.queryset.all()
    return self.queryset.filter(tenant=user.tenant)

# Böylece cross-tenant obje bulunamaz → 404
```

---

## 📋 KONTROL LİSTESİ

### Admin Endpoint'ler
- [ ] TenantDashboardView → IsAdminOrSuperAdmin
- [ ] AdminUserViewSet → IsAdminOrSuperAdmin
- [ ] AdminCourseViewSet → IsAdminOrSuperAdmin
- [ ] AdminClassGroupViewSet → IsAdminOrSuperAdmin
- [ ] AdminOpsInboxViewSet → IsAdminOrSuperAdmin
- [ ] AdminReportsViewSet → IsAdminOrSuperAdmin
- [ ] AdminRolesViewSet → IsAdminOrSuperAdmin
- [ ] AdminTenantsViewSet → IsSuperAdmin
- [ ] SystemStatsView → IsSuperAdmin
- [ ] TechLogsViewSet → IsAdminOrSuperAdmin
- [ ] ActivityLogsViewSet → IsAdminOrSuperAdmin
- [ ] FinanceViews → IsAdminOrSuperAdmin
- [ ] GlobalLiveSessionsViewSet → IsAdminOrSuperAdmin

### Users Endpoint
- [ ] UserViewSet list → IsAdminOrSuperAdmin
- [ ] UserViewSet create → IsAdminOrSuperAdmin
- [ ] UserViewSet update → IsOwnerOrAdmin
- [ ] UserViewSet delete → IsAdminOrSuperAdmin

### Course Endpoint
- [ ] Course list queryset → Draft filter by role
- [ ] Course update → IsOwnerOrAdmin
- [ ] Course delete → IsOwnerOrAdmin

### Multi-tenant
- [ ] Tüm queryset'ler tenant filter uygulasın
- [ ] Cross-tenant erişim 404 dönsün

---

## 🧪 TEST SONRASI BEKLENTİLER

### Permission Matrix Değişiklikleri

| Endpoint | Student (Önce) | Student (Sonra) |
|----------|----------------|-----------------|
| GET /api/v1/admin/dashboard/ | 200 | 403 |
| GET /api/v1/admin/users/ | 200 | 403 |
| GET /api/v1/admin/courses/ | 200 | 403 |
| POST /api/v1/admin/users/ | 400 | 403 |

| Endpoint | Instructor (Önce) | Instructor (Sonra) |
|----------|-------------------|---------------------|
| GET /api/v1/admin/dashboard/ | 200 | 403 |
| GET /api/v1/admin/users/ | 200 | 403 |
| PATCH /api/v1/courses/{other}/ | 200 | 403 |

---

## ⚠️ ÖNEMLİ NOTLAR

1. **Geriye Dönük Uyumluluk:** Frontend'de admin sayfalarına student/instructor erişimi engellenmeli
2. **Migration:** Mevcut veriler etkilenmez, sadece API erişimi kısıtlanır
3. **Test:** Tüm rol kombinasyonları test edilmeli
4. **Rollback:** Permission class'ları kaldırılarak eski davranışa dönülebilir

---

**Son Güncelleme:** 29 Aralık 2024

