# 📋 Skip Test Registry

> **Tarih:** 29 Aralık 2024  
> **Toplam Skip:** 59 test  
> **Amaç:** Her skip'in nedeni, owner'ı ve hedef sprint'i

---

## 📊 KATEGORİ DAĞILIMI

```
┌────────────────────────────────────────────────────────────────────┐
│                      SKIP KATEGORİLERİ                             │
├────────────────────────────────────────────────────────────────────┤
│ ENDPOINT_NOT_IMPLEMENTED     │████████████████████████████│ 35 (59%) │
│ FEATURE_NOT_IMPLEMENTED      │████████████░░░░░░░░░░░░░░░░│ 17 (29%) │
│ DB/MIGRATION_ISSUE           │████░░░░░░░░░░░░░░░░░░░░░░░░│  7 (12%) │
└────────────────────────────────────────────────────────────────────┘
```

---

## 🔴 ENDPOINT_NOT_IMPLEMENTED (35 test)

### Course Workflow Endpoints (5 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S01 | `test_submit_for_review` | `POST /courses/{slug}/submit_for_review/` | ✅ Evet | Backend | Sprint 2 |
| S02 | `test_publish_requires_fields` | `POST /courses/{slug}/approve/` | ✅ Evet | Backend | Sprint 2 |
| S03 | `test_publish_success` | `POST /courses/{slug}/approve/` | ✅ Evet | Backend | Sprint 2 |
| S04 | `test_request_revision` | `POST /courses/{slug}/request_revision/` | ❌ Hayır | - | Backlog |
| S05 | `test_student_cannot_publish` | `POST /courses/{slug}/approve/` | ✅ Evet | Backend | Sprint 2 |

### Enrollment Endpoints (3 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S06 | `test_cancel_enrollment` | `POST /enrollments/{id}/cancel/` | ✅ Evet | Backend | Sprint 2 |
| S07 | `test_cancel_enrollment_permissions` | `POST /enrollments/{id}/cancel/` | ✅ Evet | Backend | Sprint 2 |
| S08 | `test_enroll_already_enrolled` | `POST /courses/{slug}/enroll/` | ⚠️ Kısmi | Backend | Sprint 2 |

### Auth Endpoints (3 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S09 | `test_change_password_success` | `POST /auth/change-password/` | ✅ Evet | Backend | Sprint 1 |
| S10 | `test_change_password_wrong_old` | `POST /auth/change-password/` | ✅ Evet | Backend | Sprint 1 |
| S11 | `test_change_password_mismatch` | `POST /auth/change-password/` | ✅ Evet | Backend | Sprint 1 |

### Course Module/Content Endpoints (4 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S12 | `test_list_modules` | `GET /courses/{slug}/modules/` | ❌ Hayır | - | Backlog |
| S13 | `test_instructor_can_create_module` | `POST /courses/{slug}/modules/` | ❌ Hayır | - | Backlog |
| S14 | `test_reorder_modules` | `POST /courses/{slug}/modules/reorder/` | ❌ Hayır | - | Backlog |
| S15 | `test_content_progress` | `GET /courses/{slug}/contents/{id}/progress/` | ❌ Hayır | - | Backlog |

### Student API Endpoints (5 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S16 | `test_list_content_progress` | `GET /student/content/` | ❌ Hayır | - | Backlog |
| S17 | `test_mark_content_complete` | `POST /student/content/{id}/complete/` | ❌ Hayır | - | Backlog |
| S18 | `test_student_schedule` | `GET /student/schedule/` | ❌ Hayır | - | Backlog |
| S19 | `test_student_calendar` | `GET /student/calendar/` | ❌ Hayır | - | Backlog |
| S20 | `test_student_recommendations` | `GET /student/recommendations/` | ❌ Hayır | - | Backlog |

### Instructor API Endpoints (5 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S21 | `test_instructor_courses` | `GET /instructor/courses/` | ⚠️ Kısmi | Backend | Sprint 3 |
| S22 | `test_instructor_reorder_lessons` | `POST /instructor/courses/{id}/reorder/` | ❌ Hayır | - | Backlog |
| S23 | `test_instructor_student_roster` | `GET /instructor/courses/{id}/students/` | ⚠️ Kısmi | Backend | Sprint 3 |
| S24 | `test_instructor_analytics` | `GET /instructor/analytics/` | ❌ Hayır | - | Backlog |
| S25 | `test_instructor_earnings` | `GET /instructor/earnings/` | ❌ Hayır | - | Backlog |

### Admin API Endpoints (5 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S26 | `test_admin_audit_logs` | `GET /admin/audit-logs/` | ❌ Hayır | - | Backlog |
| S27 | `test_admin_bulk_import` | `POST /admin/users/bulk-import/` | ❌ Hayır | - | Backlog |
| S28 | `test_admin_bulk_export` | `GET /admin/users/export/` | ❌ Hayır | - | Backlog |
| S29 | `test_admin_tenant_settings` | `PATCH /admin/settings/` | ❌ Hayır | - | Backlog |
| S30 | `test_admin_system_health` | `GET /admin/system/health/` | ❌ Hayır | - | Backlog |

### Certificate Endpoints (5 test)

| # | Test | Endpoint | MVP? | Owner | Sprint |
|---|------|----------|------|-------|--------|
| S31 | `test_get_certificate` | `GET /certificates/{id}/` | ❌ Hayır | - | Backlog |
| S32 | `test_download_certificate` | `GET /certificates/{id}/download/` | ❌ Hayır | - | Backlog |
| S33 | `test_verify_certificate` | `GET /certificates/verify/{code}/` | ❌ Hayır | - | Backlog |
| S34 | `test_list_certificates` | `GET /certificates/` | ❌ Hayır | - | Backlog |
| S35 | `test_auto_generate_certificate` | `POST /enrollments/{id}/certificate/` | ❌ Hayır | - | Backlog |

---

## 🟠 FEATURE_NOT_IMPLEMENTED (17 test)

### Audit Logging (6 test)

| # | Test | Feature | MVP? | Owner | Sprint |
|---|------|---------|------|-------|--------|
| S36 | `test_login_creates_audit_log` | Login audit event | ❌ Hayır | - | Backlog |
| S37 | `test_login_fail_creates_audit_log` | Login fail audit | ❌ Hayır | - | Backlog |
| S38 | `test_logout_creates_audit_log` | Logout audit event | ❌ Hayır | - | Backlog |
| S39 | `test_user_create_audit_log` | User create audit | ❌ Hayır | - | Backlog |
| S40 | `test_role_change_audit_log` | Role change audit | ❌ Hayır | - | Backlog |
| S41 | `test_course_publish_audit_log` | Course publish audit | ❌ Hayır | - | Backlog |

### Token/Auth Features (3 test)

| # | Test | Feature | MVP? | Owner | Sprint |
|---|------|---------|------|-------|--------|
| S42 | `test_refresh_token_expired` | freeze_time integration | ❌ Hayır | Test | Backlog |
| S43 | `test_logout_blacklists_token` | JWT blacklist | ⚠️ Kısmi | Backend | Sprint 2 |
| S44 | `test_brute_force_throttle` | Login throttle | ⚠️ Kısmi | Backend | Sprint 3 |

### Activity Tracking (4 test)

| # | Test | Feature | MVP? | Owner | Sprint |
|---|------|---------|------|-------|--------|
| S45 | `test_course_activity_log` | Course activity | ❌ Hayır | - | Backlog |
| S46 | `test_user_activity_timeline` | Activity timeline | ❌ Hayır | - | Backlog |
| S47 | `test_engagement_metrics` | Engagement calc | ❌ Hayır | - | Backlog |
| S48 | `test_completion_analytics` | Completion analytics | ❌ Hayır | - | Backlog |

### Notification Features (4 test)

| # | Test | Feature | MVP? | Owner | Sprint |
|---|------|---------|------|-------|--------|
| S49 | `test_enrollment_notification` | Enrollment notify | ❌ Hayır | - | Backlog |
| S50 | `test_course_complete_notification` | Completion notify | ❌ Hayır | - | Backlog |
| S51 | `test_assignment_due_notification` | Due date notify | ❌ Hayır | - | Backlog |
| S52 | `test_mark_notification_read` | Mark read | ❌ Hayır | - | Backlog |

---

## 🟡 DB/MIGRATION_ISSUE (7 test)

### Foreign Key / Cascade Issues (3 test)

| # | Test | Sorun | Çözüm | Owner | Sprint |
|---|------|-------|-------|-------|--------|
| S53 | `test_last_accessed_content_null` | live_livesession cascade | FK constraint check | Backend | Sprint 1 |
| S54 | `test_content_delete_cascade` | Content delete cascade | ON DELETE SET NULL | Backend | Sprint 1 |
| S55 | `test_enrollment_soft_delete` | Soft delete impl | is_deleted field | Backend | Sprint 2 |

### NOT NULL Constraint Issues (3 test)

| # | Test | Sorun | Çözüm | Owner | Sprint |
|---|------|-------|-------|-------|--------|
| S56 | `test_watch_window_create` | session_id NOT NULL | Mock PlaybackSession | Test | Sprint 1 |
| S57 | `test_watch_window_duration` | session_id NOT NULL | Mock PlaybackSession | Test | Sprint 1 |
| S58 | `test_watch_window_str` | session_id NOT NULL | Mock PlaybackSession | Test | Sprint 1 |

### Unique Constraint Issues (1 test)

| # | Test | Sorun | Çözüm | Owner | Sprint |
|---|------|-------|-------|-------|--------|
| S59 | `test_email_tenant_unique` | Tenant-scoped unique | Composite unique | Backend | Backlog |

---

## 📊 MVP ÖZET

### MVP'de Olması Gerekenler (15 test)

| Kategori | Test Sayısı | Sprint |
|----------|-------------|--------|
| Course Workflow | 4 | Sprint 2 |
| Enrollment Cancel | 3 | Sprint 2 |
| Auth Change Password | 3 | Sprint 1 |
| DB Fixes | 5 | Sprint 1-2 |

### Backlog'a Ertelenen (44 test)

| Kategori | Test Sayısı | Neden |
|----------|-------------|-------|
| Audit Logging | 6 | Phase 2 feature |
| Notifications | 4 | Phase 2 feature |
| Certificate | 5 | Phase 3 feature |
| Analytics | 4 | Phase 2 feature |
| Advanced API | 15+ | Nice-to-have |

---

## 🎯 SPRINT PLANI

### Sprint 1 (Hafta 1)
- [ ] Auth change-password endpoint (S09-S11)
- [ ] DB FK constraint fixes (S53-S55)
- [ ] Test mock fixes (S56-S58)

### Sprint 2 (Hafta 2)
- [ ] Course workflow endpoints (S01-S03, S05)
- [ ] Enrollment cancel endpoint (S06-S08)
- [ ] JWT blacklist (S43)

### Sprint 3 (Hafta 3-4)
- [ ] Instructor basic endpoints (S21, S23)
- [ ] Login throttle (S44)

### Backlog (Post-MVP)
- [ ] Certificate system
- [ ] Audit logging
- [ ] Notifications
- [ ] Analytics
- [ ] Advanced admin features

---

## 📝 SKIP MARKER KULLANIMI

Test dosyalarında skip reason formatı:

```python
@pytest.mark.skip(reason="ENDPOINT_NOT_IMPLEMENTED: POST /courses/{slug}/approve/")
def test_publish_success():
    pass

@pytest.mark.skip(reason="FEATURE_NOT_IMPLEMENTED: Audit logging")
def test_login_creates_audit_log():
    pass

@pytest.mark.skip(reason="DB_ISSUE: live_livesession cascade constraint")
def test_last_accessed_content_null():
    pass
```

---

**Son Güncelleme:** 29 Aralık 2024

