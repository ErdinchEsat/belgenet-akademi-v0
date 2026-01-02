# Backend Unit Test - Kapsamlı Todo List

> **Referans:** `test_plan.md`
> **Son Güncelleme:** 29 Aralık 2024
> **Durum Göstergeleri:** ⬜ Bekliyor | 🔄 Devam Ediyor | ✅ Tamamlandı | ⏭️ Atlandı

---

## AŞAMA 0: Test Altyapısı Kurulumu [P0] ✅

### 0.1 Bağımlılık Yönetimi
- [x] `tools/requirements/dev.txt` güncelle
  - [x] `pytest>=7.4.0` ekle
  - [x] `pytest-django>=4.5.0` ekle
  - [x] `pytest-xdist>=3.3.0` ekle (paralel test)
  - [x] `pytest-cov>=4.1.0` ekle (coverage)
  - [x] `pytest-timeout>=2.2.0` ekle
  - [x] `factory-boy>=3.3.0` ekle
  - [x] `freezegun>=1.2.0` ekle
  - [x] `responses>=0.24.0` ekle
  - [x] `faker>=19.0.0` ekle

### 0.2 Dizin Yapısı Oluşturma
- [x] `tests/akademi/unit/` dizini oluştur
  - [x] `__init__.py` ekle
- [x] `tests/akademi/api/` dizini oluştur
  - [x] `__init__.py` ekle
- [x] `tests/akademi/integration/` dizini oluştur
  - [x] `__init__.py` ekle
- [x] `tests/akademi/permissions/` dizini oluştur
  - [x] `__init__.py` ekle

### 0.3 Pytest Konfigürasyonu
- [x] `tests/akademi/pytest.ini` oluştur
  - [x] DJANGO_SETTINGS_MODULE ayarla
  - [x] Test discovery pattern'ları tanımla
  - [x] Marker'ları tanımla (unit, api, integration, slow, tenant)
  - [x] Coverage ayarları ekle
  - [x] Timeout ayarla

### 0.4 Factory Boy Factories
- [x] `tests/akademi/fixtures/factories.py` oluştur
  - [x] `TenantFactory` implement et
    - [x] name, slug, type, is_active alanları
    - [x] Faker ile Türkçe veri
  - [x] `UserFactory` implement et
    - [x] email, first_name, last_name, role, tenant
    - [x] password post_generation hook
    - [x] Rol parametresi (STUDENT, INSTRUCTOR, ADMIN)
  - [x] `CourseFactory` implement et
    - [x] title, slug, description, tenant, status
    - [x] ManyToMany instructors için trait
  - [x] `CourseModuleFactory` implement et
    - [x] course, title, order
  - [x] `CourseContentFactory` implement et
    - [x] module, title, type, duration_minutes
  - [x] `EnrollmentFactory` implement et
    - [x] user, course, status, progress_percent
  - [x] `ClassGroupFactory` implement et
  - [x] `AssignmentFactory` implement et
  - [x] `QuizFactory` implement et
  - [x] `QuizQuestionFactory` implement et

### 0.5 Test Helpers
- [x] `tests/akademi/fixtures/helpers.py` oluştur
  - [x] `create_auth_client(user, tenant)` fonksiyonu
  - [x] `create_token_client(user)` fonksiyonu
  - [x] `@contextmanager audit_capture()` implement et
  - [x] `AssertHelpers` sınıfı
    - [x] `assert_tenant_isolated(queryset, tenant)`
    - [x] `assert_error_format(response_data)`
    - [x] `assert_no_pii_leak(data, fields)`
    - [x] `assert_pagination(response_data)`
    - [x] `assert_status_code(response, expected)`

### 0.6 Ana conftest.py Güncelleme
- [x] `tests/akademi/conftest.py` güncelle
  - [x] Path konfigürasyonu düzenle
  - [x] `pytest_configure()` güncelle
  - [x] Tenant fixtures ekle
    - [x] `tenant_a` (primary)
    - [x] `tenant_b` (isolation tests)
  - [x] User fixtures ekle
    - [x] `admin_a` (TENANT_ADMIN)
    - [x] `instructor_a` (INSTRUCTOR)
    - [x] `student_a` (STUDENT)
    - [x] `student_b` (Tenant B)
    - [x] `super_admin` (SUPER_ADMIN)
    - [x] `deactivated_user`
  - [x] Course fixtures ekle
    - [x] `course_draft_a`
    - [x] `course_published_a`
    - [x] `course_published_b`
  - [x] Enrollment fixtures ekle
    - [x] `enrollment_a`
  - [x] API Client fixtures ekle
    - [x] `api_client` (unauthenticated)
    - [x] `anon_client` (alias)
    - [x] `student_client`
    - [x] `instructor_client`
    - [x] `admin_client`
    - [x] `super_admin_client`
  - [x] Utility fixtures ekle
    - [x] `audit_capture`
    - [x] `freeze_time`

### 0.7 Doğrulama
- [x] Factory'leri test et (`pytest --collect-only`)
- [x] Fixture'ları test et (basit bir test yaz)
- [x] Django setup çalışıyor mu kontrol et

---

## AŞAMA 1: User Model Testleri [P0] ✅

### 1.1 Test Dosyası Oluşturma
- [x] `tests/akademi/unit/test_user_model.py` oluştur
  - [x] Gerekli import'ları ekle
  - [x] Test class yapısını hazırla

### 1.2 Validation Testleri (U-01 ~ U-03)
- [x] `TestUserModelValidation` sınıfı
  - [x] `test_required_fields_validation` (U-01)
    - [x] Email None ile create
    - [x] ValueError beklentisi
    - [x] Hata mesajı kontrolü
  - [x] `test_email_unique_within_tenant` (U-02)
    - [x] Aynı tenant'ta duplicate email
    - [x] IntegrityError beklentisi
  - [x] `test_email_across_tenants` (U-03)
    - [x] Farklı tenant'larda aynı email
    - [x] Global unique vs tenant-scoped kontrolü
  - [x] `test_invalid_email_format`
    - [x] Geçersiz email formatı
  - [x] `test_role_choices_validation`
    - [x] Geçersiz rol değeri

### 1.3 Password Security Testleri (U-04)
- [x] `TestUserPasswordSecurity` sınıfı
  - [x] `test_password_hashing` (U-04)
    - [x] Plain text saklanmıyor
    - [x] Hash algoritması kontrolü
    - [x] check_password çalışıyor
  - [x] `test_password_validation`
    - [x] Minimum uzunluk
    - [x] Karmaşıklık kuralları
  - [x] `test_password_change`
    - [x] set_password çalışıyor

### 1.4 Deactivation Testleri (U-05)
- [x] `TestUserDeactivation` sınıfı
  - [x] `test_deactivate_blocks_login` (U-05)
    - [x] is_active = False
    - [x] Login attempt → 401/403
  - [x] `test_deactivate_blocks_token_refresh`
    - [x] Refresh token çalışmıyor
  - [x] `test_reactivate_allows_login`
    - [x] is_active = True → login başarılı

### 1.5 Audit Logging Testleri (U-06)
- [x] `TestUserAuditLogging` sınıfı
  - [x] `test_role_assignment_audit` (U-06)
    - [x] Rol değişikliği audit event
    - [x] Event içeriği kontrolü
  - [x] `test_user_create_audit`
    - [x] User oluşturma audit event
  - [x] `test_user_update_audit`
    - [x] Profil güncelleme audit event

### 1.6 Model Property Testleri
- [x] `TestUserProperties` sınıfı
  - [x] `test_full_name_property`
  - [x] `test_name_property_alias`
  - [x] `test_tenant_id_property`
  - [x] `test_is_student_property`
  - [x] `test_is_instructor_property`
  - [x] `test_get_avatar_url`

---

## AŞAMA 2: Authentication API Testleri [P0] ✅

### 2.1 Test Dosyası Oluşturma
- [x] `tests/akademi/api/test_auth_api.py` oluştur
  - [x] Import'ları ekle
  - [x] Test class yapısını hazırla

### 2.2 Login Endpoint Testleri (AUTH-01 ~ AUTH-03)
- [x] `TestLoginEndpoint` sınıfı
  - [x] `test_login_success` (AUTH-01)
    - [x] Doğru credentials
    - [x] access token döner
    - [x] refresh token döner
    - [x] user bilgisi döner
  - [x] `test_login_wrong_password` (AUTH-02)
    - [x] Yanlış şifre → 401
    - [x] Hata mesajı bilgi sızdırmıyor
  - [x] `test_login_deactivated_user` (AUTH-03)
    - [x] is_active = False → 401/403
  - [x] `test_login_nonexistent_email`
    - [x] Olmayan email → 401
  - [x] `test_login_empty_credentials`
    - [x] Boş email/password → 400
  - [x] `test_login_creates_audit_log`
    - [x] Başarılı login audit event
  - [x] `test_login_fail_creates_audit_log`
    - [x] Başarısız login audit event

### 2.3 Token Refresh Testleri (AUTH-04 ~ AUTH-05)
- [x] `TestTokenRefresh` sınıfı
  - [x] `test_refresh_token_success` (AUTH-04)
    - [x] Geçerli refresh → yeni access
    - [x] Access token farklı
  - [x] `test_refresh_token_expired` (AUTH-05)
    - [x] Expired refresh → 401
    - [x] freezegun ile zaman simülasyonu
  - [x] `test_refresh_token_invalid`
    - [x] Geçersiz refresh → 401
  - [x] `test_refresh_token_malformed`
    - [x] Malformed token → 401

### 2.4 Logout Testleri (AUTH-06)
- [x] `TestLogout` sınıfı
  - [x] `test_logout_blacklists_token` (AUTH-06)
    - [x] Logout sonrası refresh invalid
  - [x] `test_logout_requires_auth`
    - [x] Unauthenticated → 401
  - [x] `test_logout_creates_audit_log`
    - [x] Logout audit event

### 2.5 Throttle Testleri (AUTH-07)
- [x] `TestBruteForceProtection` sınıfı
  - [x] `test_brute_force_throttle` (AUTH-07)
    - [x] N kez fail → 429
    - [x] Throttle süresi kontrolü

### 2.6 Register Testleri
- [x] `TestRegister` sınıfı
  - [x] `test_register_success`
  - [x] `test_register_duplicate_email`
  - [x] `test_register_weak_password`
  - [x] `test_register_password_mismatch`

### 2.7 Me Endpoint Testleri
- [x] `TestMeEndpoint` sınıfı
  - [x] `test_get_me_authenticated`
  - [x] `test_get_me_unauthenticated`
  - [x] `test_patch_me_allowed_fields`
  - [x] `test_patch_me_forbidden_fields`

---

## AŞAMA 3: Course API Testleri [P0] ✅

### 3.1 Test Dosyası Oluşturma
- [x] `tests/akademi/api/test_course_api.py` oluştur

### 3.2 Course Create Testleri (C-01 ~ C-02)
- [x] `TestCourseCreate` sınıfı
  - [x] `test_instructor_create_course` (C-01)
    - [x] Instructor → 201
    - [x] status = draft
    - [x] tenant = instructor.tenant
    - [x] instructors.add(instructor)
  - [x] `test_student_create_forbidden` (C-02)
    - [x] Student → 403
  - [x] `test_admin_create_course`
    - [x] Admin → 201
  - [x] `test_create_course_validation`
    - [x] Required fields kontrolü
  - [x] `test_create_course_slug_unique`
    - [x] Duplicate slug → 400

### 3.3 Course Visibility Testleri (C-03)
- [x] `TestCourseVisibility` sınıfı
  - [x] `test_draft_not_visible_to_student` (C-03)
    - [x] Student → draft görmez
  - [x] `test_draft_visible_to_owner`
    - [x] Owner instructor → draft görür
  - [x] `test_draft_visible_to_admin`
    - [x] Admin → draft görür
  - [x] `test_published_visible_to_all`
    - [x] Tüm roller → published görür

### 3.4 Course Publish Testleri (C-04 ~ C-05)
- [x] `TestCoursePublish` sınıfı
  - [x] `test_publish_requires_fields` (C-04)
    - [x] Eksik alanlar → 400
  - [x] `test_publish_success` (C-05)
    - [x] Geçerli kurs → 200
    - [x] status = published
    - [x] is_published = True
    - [x] publish_at set edildi
  - [x] `test_submit_for_review`
    - [x] draft → pending_admin_setup
  - [x] `test_request_revision`
    - [x] Admin revision note
  - [x] `test_publish_creates_audit_log`

### 3.5 Course Update Testleri (C-06)
- [x] `TestCourseUpdate` sınıfı
  - [x] `test_update_only_owner` (C-06)
    - [x] Başka instructor → 403
  - [x] `test_owner_can_update`
    - [x] Owner → 200
  - [x] `test_admin_can_update`
    - [x] Admin override
  - [x] `test_update_published_restrictions`
    - [x] Published kursta bazı alanlar değişmez

### 3.6 Course Filtering Testleri (C-07)
- [x] `TestCourseFiltering` sınıfı
  - [x] `test_course_list_filtering` (C-07)
    - [x] category filtresi
    - [x] level filtresi
    - [x] status filtresi
    - [x] search filtresi
  - [x] `test_course_list_pagination`
  - [x] `test_course_list_ordering`

### 3.7 Tenant Isolation Testleri (C-08)
- [x] `TestCourseTenantIsolation` sınıfı
  - [x] `test_tenant_isolation` (C-08)
    - [x] Tenant B kursuna erişim → 404/403
  - [x] `test_super_admin_sees_all_tenants`
    - [x] Super admin → tüm tenantlar

---

## AŞAMA 4: Enrollment Testleri [P1] ✅

### 4.1 Test Dosyası Oluşturma
- [x] `tests/akademi/api/test_enrollment_api.py` oluştur

### 4.2 Enroll Testleri (E-01 ~ E-03)
- [x] `TestEnrollment` sınıfı
  - [x] `test_enroll_free_course` (E-01)
    - [x] Free published course → 201
    - [x] status = active
  - [x] `test_enroll_draft_forbidden` (E-02)
    - [x] Draft course → 400/403
  - [x] `test_duplicate_enroll_idempotent` (E-03)
    - [x] İkinci enroll → 200/409
    - [x] Enrollment count artmaz
  - [x] `test_enroll_increments_course_count`
    - [x] enrolled_count += 1

### 4.3 Cancel Enrollment Testleri (E-04)
- [x] `TestEnrollmentCancel` sınıfı
  - [x] `test_cancel_enrollment` (E-04)
    - [x] status = cancelled
  - [x] `test_cancel_creates_audit_log`

### 4.4 Cross-Tenant Testleri (E-05)
- [x] `TestEnrollmentTenantIsolation` sınıfı
  - [x] `test_cross_tenant_enroll_forbidden` (E-05)
    - [x] Tenant A user → Tenant B course → 404/403

### 4.5 Progress Testleri
- [x] `TestEnrollmentProgress` sınıfı
  - [x] `test_complete_content`
  - [x] `test_progress_update`
  - [x] `test_enrollment_complete_on_threshold`

---

## AŞAMA 5: Student/Instructor/Admin API Testleri [P1] ✅

### 5.1 Student API Testleri (S-01 ~ S-05)
- [x] `tests/akademi/api/test_student_api.py` oluştur
- [x] `TestStudentProfile` sınıfı
  - [x] `test_get_self_profile` (S-01)
  - [x] `test_patch_allowed_fields_only` (S-02)
- [x] `TestStudentProgress` sınıfı
  - [x] `test_progress_write_increases` (S-03)
  - [x] `test_progress_cannot_decrease` (S-04)
  - [x] `test_unenrolled_content_forbidden` (S-05)
- [x] `TestStudentClasses` sınıfı
  - [x] `test_list_enrolled_classes`
  - [x] `test_class_detail`
- [x] `TestStudentAssignments` sınıfı
  - [x] `test_list_assignments`
  - [x] `test_submit_assignment`
- [x] `TestStudentNotifications` sınıfı
  - [x] `test_list_notifications`
  - [x] `test_mark_as_read`

### 5.2 Instructor API Testleri (I-01 ~ I-03)
- [x] `tests/akademi/api/test_instructor_api.py` oluştur
- [x] `TestInstructorCourses` sınıfı
  - [x] `test_own_course_list` (I-01)
  - [x] `test_reorder_lessons` (I-02)
  - [x] `test_roster_only_own_course` (I-03)
- [x] `TestInstructorDashboard` sınıfı
  - [x] `test_dashboard_data`
  - [x] `test_dashboard_stats`
- [x] `TestInstructorClasses` sınıfı
  - [x] `test_list_classes`
  - [x] `test_class_students`
- [x] `TestInstructorAssessments` sınıfı
  - [x] `test_list_assessments`
  - [x] `test_grade_submission`

### 5.3 Admin API Testleri (A-01 ~ A-03)
- [x] `tests/akademi/api/test_admin_api.py` oluştur
- [x] `TestAdminUsers` sınıfı
  - [x] `test_user_list_tenant_scoped` (A-01)
  - [x] `test_deactivate_user` (A-02)
  - [x] `test_bulk_import` (A-03)
  - [x] `test_create_user`
  - [x] `test_update_user_role`
- [x] `TestAdminCourses` sınıfı
  - [x] `test_approve_course`
  - [x] `test_unpublish_course`
- [x] `TestAdminDashboard` sınıfı
  - [x] `test_tenant_dashboard`
  - [x] `test_system_stats`

---

## AŞAMA 6: Audit Log Testleri [P1] ✅

### 6.1 Test Dosyası Oluşturma
- [x] `tests/akademi/integration/test_audit_log.py` oluştur

### 6.2 Event Üretimi Testleri (L-01 ~ L-02)
- [x] `TestAuditEventCreation` sınıfı
  - [x] `test_course_create_audit` (L-01)
    - [x] action = CREATE
    - [x] entity_type = Course
  - [x] `test_enrollment_complete_audit` (L-02)
    - [x] action = COMPLETE
  - [x] `test_login_audit`
  - [x] `test_role_change_audit`

### 6.3 Access Control Testleri (L-03)
- [x] `TestAuditAccessControl` sınıfı
  - [x] `test_audit_access_control` (L-03)
    - [x] Student → 403
    - [x] Admin → 200
  - [x] `test_instructor_limited_access`
    - [x] Sadece kendi entity'leri

### 6.4 PII Safety Testleri (L-04)
- [x] `TestAuditPIISafety` sınıfı
  - [x] `test_audit_pii_safety` (L-04)
    - [x] password yok
    - [x] token yok
    - [x] secret yok
  - [x] `test_login_fail_no_password_leak`

---

## AŞAMA 7: Permission Matrix Testleri [P2] ✅

### 7.1 Test Dosyası Oluşturma
- [x] `tests/akademi/permissions/test_permission_matrix.py` oluştur

### 7.2 Matrix Tanımlama
- [x] `PERMISSION_MATRIX` listesi oluştur
  - [x] Auth endpoints
    - [x] `/api/v1/auth/token/` POST
    - [x] `/api/v1/auth/refresh/` POST
    - [x] `/api/v1/auth/me/` GET, PATCH
    - [x] `/api/v1/auth/logout/` POST
  - [x] Course endpoints
    - [x] `/api/v1/courses/` GET, POST
    - [x] `/api/v1/courses/{slug}/` GET, PATCH, DELETE
    - [x] `/api/v1/courses/{slug}/enroll/` POST
    - [x] `/api/v1/courses/{slug}/approve/` POST
  - [x] User endpoints
    - [x] `/api/v1/users/` GET, POST
    - [x] `/api/v1/users/{id}/` GET, PATCH, DELETE
  - [x] Student endpoints
    - [x] `/api/v1/student/classes/` GET
    - [x] `/api/v1/student/assignments/` GET
  - [x] Instructor endpoints
    - [x] `/api/v1/instructor/dashboard/` GET
    - [x] `/api/v1/instructor/classes/` GET
  - [x] Admin endpoints
    - [x] `/api/v1/admin/dashboard/` GET
    - [x] `/api/v1/admin/users/` GET

### 7.3 Parametrize Test
- [x] `test_permission_matrix` implement et
  - [x] Tüm rol kombinasyonları
  - [x] Tüm HTTP methodları
  - [x] Hata durumlarında detaylı mesaj

---

## AŞAMA 8: Entegrasyon ve Workflow Testleri [P2] ✅

### 8.1 Multi-Tenant Testleri
- [x] `tests/akademi/integration/test_multi_tenant.py` oluştur
  - [x] `test_user_data_isolation`
  - [x] `test_course_data_isolation`
  - [x] `test_enrollment_data_isolation`
  - [x] `test_audit_data_isolation`

### 8.2 Workflow Testleri
- [x] `tests/akademi/integration/test_workflow.py` oluştur
  - [x] `test_course_lifecycle`
    - [x] draft → pending → published
  - [x] `test_enrollment_lifecycle`
    - [x] enroll → progress → complete → certificate
  - [x] `test_assignment_lifecycle`
    - [x] create → submit → grade

---

## AŞAMA 9: CI/CD ve Final [P2] ✅

### 9.1 GitHub Actions
- [x] `.github/workflows/tests.yml` oluştur
  - [x] PostgreSQL service
  - [x] Python setup
  - [x] Dependencies install
  - [x] Pytest run
  - [x] Coverage upload

### 9.2 Coverage Raporu
- [x] Coverage threshold ≥80% doğrula
- [x] Coverage report generate et
- [x] Eksik alanları tespit et

### 9.3 Dokümantasyon
- [x] `change_log.md` güncelle
- [x] Test run instructions ekle
- [x] README güncelle

---

## İlerleme Takibi

| Aşama | Toplam | Tamamlanan | Yüzde |
|-------|--------|------------|-------|
| 0 - Altyapı | 45 | 45 | 100% ✅ |
| 1 - User Model | 25 | 25 | 100% ✅ |
| 2 - Auth API | 30 | 30 | 100% ✅ |
| 3 - Course API | 35 | 35 | 100% ✅ |
| 4 - Enrollment | 15 | 15 | 100% ✅ |
| 5 - S/I/A API | 40 | 40 | 100% ✅ |
| 6 - Audit Log | 15 | 15 | 100% ✅ |
| 7 - Permissions | 10 | 10 | 100% ✅ |
| 8 - Integration | 10 | 10 | 100% ✅ |
| 9 - CI/CD | 10 | 10 | 100% ✅ |
| **TOPLAM** | **235** | **235** | **100%** 🎉

---

## Başlangıç Komutu

```bash
cd /Users/esat/Desktop/BelgeNet/v0/MAYSCON/mayscon.v1
pytest tests/akademi/ --collect-only
```

---

**Son Güncelleme:** 29 Aralık 2024
