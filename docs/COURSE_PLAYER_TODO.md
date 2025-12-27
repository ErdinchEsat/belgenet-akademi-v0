# B1. COURSE PLAYER — ENTEGRASYON PLANI VE TODO LİSTESİ

> ✅ **PHASE 1 MVP TAMAMLANDI** (27 Aralık 2025)
> 
> Oluşturulan app'ler: `player`, `progress`, `telemetry`, `sequencing`, `quizzes`

## 📊 MEVCUT PROJE ANALİZİ

### Proje Yapısı
```
v0/AKADEMI/
├── akademi/                 # Django proje ayarları
│   ├── settings.py          # Multi-DB (primary, analytics, logs, media)
│   └── urls.py               # API routing
├── backend/
│   ├── tenants/             # ✅ Multi-tenant yapı hazır
│   │   └── models.py        # Tenant, TenantSettings
│   ├── users/               # ✅ Custom User modeli hazır
│   │   └── models.py        # User, UserProfile
│   ├── courses/             # ⚠️ Temel yapı var, genişletilecek
│   │   └── models.py        # Course, CourseModule, CourseContent, Enrollment, ContentProgress
│   ├── instructor/          # ✅ Eğitmen API'leri
│   ├── student/             # ✅ Öğrenci modülleri
│   └── admin_api/           # ✅ Admin API'leri
└── frontend/                # React + TypeScript frontend
```

### Mevcut Modeller (courses/models.py)
| Model | Durum | Notlar |
|-------|-------|--------|
| `Course` | ✅ Var | tenant, instructors, status, completion_percent var |
| `CourseModule` | ✅ Var | order, is_published var |
| `CourseContent` | ✅ Var | type, data, duration_minutes, is_locked var |
| `Enrollment` | ✅ Var | progress_percent, completed_contents, last_accessed_content var |
| `ContentProgress` | ⚠️ Temel | watched_seconds, last_position_seconds var AMA session yok |

### Mevcut Eksiklikler
1. ❌ `PlaybackSession` modeli yok (session tracking)
2. ❌ `TelemetryEvent` modeli yok (event logging)
3. ❌ `ContentLockPolicy` modeli yok (policy engine)
4. ❌ `TimelineNode` modeli yok (interactive overlay)
5. ❌ Quiz için dedicated modeller yok
6. ❌ AI artifacts modelleri yok
7. ❌ User preferences (speed, caption) tam değil

---

## 🏗️ ENTEGRASYON STRATEJİSİ

### Yaklaşım: Bounded Context App'leri
Mevcut `courses` app'ini bozmadan, yeni modüler app'ler ekliyoruz:

```
backend/
├── courses/           # ✅ Mevcut (dokunulmuyor)
├── player/            # 🆕 Playback session + signed URL
├── progress/          # 🆕 Advanced progress tracking
├── telemetry/         # 🆕 Event ingestion + analytics
├── sequencing/        # 🆕 Lock policies + unlock engine
├── timeline/          # 🆕 Interactive overlay nodes
├── quizzes/           # 🆕 Quiz system
├── notes/             # 🆕 Notes, threads, highlights
├── ai/                # 🆕 Transcripts, RAG, tutor
├── recommendations/   # 🆕 Adaptive learning (Phase 3)
└── integrity/         # 🆕 Academic integrity (Phase 3)
```

### Ortak Kütüphaneler
```
backend/
└── libs/
    ├── idempotency/       # Idempotency-Key middleware
    ├── storage/           # Signed URL generation
    ├── events/            # Event schema + dispatch
    └── tenant_aware/      # TenantAwareModel base class
```

---

## 🟢 PHASE 1 — MVP-1 (Core LMS + Güvenli İzleme)

> **Hedef:** Stabil, ölçülebilir, kilitli LMS video oynatıcıyı canlıya almak

### 1.1 Libs Altyapısı
```markdown
- [ ] `backend/libs/__init__.py` oluştur
- [ ] `backend/libs/tenant_aware/` - TenantAwareModel base class
- [ ] `backend/libs/idempotency/` - Idempotency middleware + helpers
- [ ] `backend/libs/storage/` - Signed URL generation (S3/Azure/Local)
```

### 1.2 Player App (Playback Session)
```markdown
backend/player/
├── __init__.py
├── apps.py
├── models.py           # PlaybackSession
├── serializers.py
├── views.py            # SessionViewSet
├── services/
│   ├── session_service.py
│   └── token_service.py  # Signed URL generation
├── urls.py
└── tests/
```

**Modeller:**
```python
# PlaybackSession
- id: UUID (PK)
- tenant_id: UUID (FK → Tenant)
- user_id: UUID (FK → User)
- course_id: UUID (FK → Course)
- content_id: UUID (FK → CourseContent)
- device_id: TEXT
- user_agent: TEXT
- ip_hash: TEXT
- started_at: TIMESTAMPTZ
- ended_at: TIMESTAMPTZ
- ended_reason: TEXT (ended|timeout|logout|error)
- last_heartbeat_at: TIMESTAMPTZ
```

**Endpoints:**
```
POST /api/v1/courses/{courseId}/content/{contentId}/sessions/
GET  /api/v1/courses/{courseId}/content/{contentId}/sessions/{sessionId}/
PUT  /api/v1/courses/{courseId}/content/{contentId}/sessions/{sessionId}/heartbeat/
PUT  /api/v1/courses/{courseId}/content/{contentId}/sessions/{sessionId}/end/
```

**TODO:**
- [ ] Player app oluştur (`python manage.py startapp player` ve backend/player'a taşı)
- [ ] PlaybackSession modeli
- [ ] Session serializers
- [ ] SessionViewSet (create, heartbeat, end)
- [ ] SignedURL service (token_service.py)
- [ ] Settings'e player app ekle
- [ ] URL'leri urls.py'a ekle
- [ ] Unit testler

### 1.3 Progress App (Gelişmiş İzleme Takibi)
```markdown
backend/progress/
├── __init__.py
├── apps.py
├── models.py           # EnhancedContentProgress, ProgressWatchWindow
├── serializers.py
├── views.py            # ProgressViewSet
├── services/
│   └── progress_service.py  # watched_seconds validation
├── urls.py
└── tests/
```

**Modeller:**
```python
# EnhancedContentProgress (mevcut ContentProgress'i genişletir veya yenisi)
- id: UUID (PK)
- tenant_id: UUID
- user_id: UUID
- course_id: UUID
- content_id: UUID
- watched_seconds: INT (seek-independent)
- last_position_seconds: INT
- completion_ratio: DECIMAL(5,4)
- is_completed: BOOLEAN
- completed_at: TIMESTAMPTZ
- last_session_id: UUID (FK → PlaybackSession)
- last_device_id: TEXT
- last_speed: DECIMAL(3,2)
- last_caption_lang: TEXT
- UNIQUE(tenant_id, user_id, content_id)

# ProgressWatchWindow (contiguous watch validation)
- id: UUID (PK)
- tenant_id: UUID
- session_id: UUID (FK → PlaybackSession)
- content_id: UUID
- user_id: UUID
- start_video_ts: INT
- end_video_ts: INT
- duration_seconds: INT
- is_verified: BOOLEAN
```

**Endpoints:**
```
GET  /api/v1/courses/{courseId}/content/{contentId}/progress/
PUT  /api/v1/courses/{courseId}/content/{contentId}/progress/
```

**Progress Update Request:**
```json
{
  "session_id": "uuid",
  "last_position_seconds": 455,
  "client_watched_delta_seconds": 10,
  "playback_rate": 1.25,
  "caption_lang": "tr",
  "client_ts": "2025-12-26T10:05:10Z"
}
```

**TODO:**
- [ ] Progress app oluştur
- [ ] EnhancedContentProgress modeli (veya mevcut ContentProgress'i migrate et)
- [ ] ProgressWatchWindow modeli (opsiyonel ama tavsiye)
- [ ] Progress serializers
- [ ] ProgressViewSet (GET, PUT)
- [ ] progress_service.py (watched_seconds server-side validation)
- [ ] Mevcut ContentProgress ile migration stratejisi
- [ ] Settings'e progress app ekle
- [ ] URL'leri urls.py'a ekle
- [ ] Unit testler

### 1.4 Telemetry App (Event Tracking)
```markdown
backend/telemetry/
├── __init__.py
├── apps.py
├── models.py           # TelemetryEvent
├── serializers.py
├── views.py            # EventBatchViewSet
├── services/
│   ├── ingest_service.py   # Batch ingestion + dedupe
│   └── aggregator.py       # Celery tasks for metrics
├── urls.py
└── tests/
```

**Modeller:**
```python
# TelemetryEvent (append-only)
- id: UUID (PK)
- tenant_id: UUID
- session_id: UUID
- user_id: UUID
- course_id: UUID
- content_id: UUID
- client_event_id: TEXT (dedupe key)
- event_type: TEXT (play|pause|seek|rate_change|timeupdate|ended|fullscreen|pip)
- video_ts: INT
- server_ts: TIMESTAMPTZ
- client_ts: TIMESTAMPTZ
- payload: JSONB
- UNIQUE(tenant_id, session_id, client_event_id)
```

**Endpoints:**
```
POST /api/v1/courses/{courseId}/content/{contentId}/events/
```

**Event Batch Request:**
```json
{
  "session_id": "uuid",
  "events": [
    {
      "client_event_id": "evt-001",
      "event_type": "play",
      "video_ts": 440,
      "client_ts": "2025-12-26T10:05:20Z",
      "payload": {"autoplay": false}
    }
  ]
}
```

**TODO:**
- [ ] Telemetry app oluştur
- [ ] TelemetryEvent modeli
- [ ] Event serializers (batch)
- [ ] EventBatchViewSet (POST)
- [ ] ingest_service.py (batch ingestion + client_event_id dedupe)
- [ ] Celery task for drop-off metrics (opsiyonel MVP-1)
- [ ] Settings'e telemetry app ekle
- [ ] URL'leri urls.py'a ekle
- [ ] Unit testler

### 1.5 Sequencing App (Content Locking)
```markdown
backend/sequencing/
├── __init__.py
├── apps.py
├── models.py           # ContentLockPolicy, ContentUnlockState
├── serializers.py
├── views.py            # LockViewSet
├── services/
│   └── policy_engine.py    # evaluate_unlock logic
├── urls.py
└── tests/
```

**Modeller:**
```python
# ContentLockPolicy
- id: UUID (PK)
- tenant_id: UUID
- course_id: UUID
- content_id: UUID
- policy_type: TEXT (min_watch_ratio|requires_prev_completed|requires_quiz_pass)
- policy_config: JSONB ({"min_ratio": 0.8})
- is_active: BOOLEAN

# ContentUnlockState
- id: UUID (PK)
- tenant_id: UUID
- user_id: UUID
- course_id: UUID
- content_id: UUID
- is_unlocked: BOOLEAN
- unlocked_at: TIMESTAMPTZ
- reason: TEXT
- state: JSONB (hangi şartlar sağlandı)
- UNIQUE(tenant_id, user_id, content_id)
```

**Endpoints:**
```
GET  /api/v1/courses/{courseId}/content/{contentId}/lock/
POST /api/v1/courses/{courseId}/content/{contentId}/lock/evaluate/
```

**TODO:**
- [ ] Sequencing app oluştur
- [ ] ContentLockPolicy modeli
- [ ] ContentUnlockState modeli
- [ ] Lock serializers
- [ ] LockViewSet (GET lock status, POST evaluate)
- [ ] policy_engine.py (evaluate_unlock service)
- [ ] Progress update sonrası auto-evaluate trigger
- [ ] Quiz submit sonrası auto-evaluate trigger
- [ ] Settings'e sequencing app ekle
- [ ] URL'leri urls.py'a ekle
- [ ] Unit testler

### 1.6 Quizzes App (Video İçi Quiz)
```markdown
backend/quizzes/
├── __init__.py
├── apps.py
├── models.py           # Quiz, QuizQuestion, QuizAttempt, QuizAnswer
├── serializers.py
├── views.py            # QuizViewSet, AttemptViewSet
├── services/
│   └── grading_service.py  # calculate_score, grade_attempt
├── urls.py
└── tests/
```

**Modeller:**
```python
# Quiz
- id: UUID (PK)
- tenant_id: UUID
- title: TEXT
- passing_score: DECIMAL(5,2)
- config: JSONB (time_limit, etc.)

# QuizQuestion
- id: UUID (PK)
- tenant_id: UUID
- quiz_id: UUID (FK)
- question_type: TEXT (mcq|multi|short|truefalse)
- prompt: TEXT
- options: JSONB
- correct_answer: JSONB
- points: DECIMAL(5,2)
- order_no: INT

# QuizAttempt
- id: UUID (PK)
- tenant_id: UUID
- quiz_id: UUID
- user_id: UUID
- course_id: UUID
- content_id: UUID (nullable - video içi ise dolu)
- session_id: UUID (nullable)
- status: TEXT (started|submitted|graded)
- score: DECIMAL(6,2)
- passed: BOOLEAN
- started_at: TIMESTAMPTZ
- submitted_at: TIMESTAMPTZ

# QuizAnswer
- id: UUID (PK)
- tenant_id: UUID
- attempt_id: UUID (FK)
- question_id: UUID
- answer: JSONB
- is_correct: BOOLEAN
- points_awarded: DECIMAL(5,2)
```

**Endpoints:**
```
GET  /api/v1/quizzes/{quizId}/
POST /api/v1/quizzes/{quizId}/attempts/
POST /api/v1/quizzes/{quizId}/attempts/{attemptId}/submit
GET  /api/v1/quizzes/{quizId}/attempts/{attemptId}/
```

**TODO:**
- [ ] Quizzes app oluştur
- [ ] Quiz, QuizQuestion, QuizAttempt, QuizAnswer modelleri
- [ ] Quiz serializers
- [ ] QuizViewSet (GET quiz with questions)
- [ ] AttemptViewSet (create, submit, get result)
- [ ] grading_service.py (calculate_score, grade_attempt)
- [ ] Submit sonrası sequencing.policy_engine.evaluate_unlock çağrısı
- [ ] Settings'e quizzes app ekle
- [ ] URL'leri urls.py'a ekle
- [ ] Unit testler

### 1.7 Settings ve URL Entegrasyonu

**akademi/settings.py eklemeleri:**
```python
INSTALLED_APPS += [
    # ... mevcut apps ...
    'backend.player',
    'backend.progress',
    'backend.telemetry',
    'backend.sequencing',
    'backend.quizzes',
]
```

**akademi/urls.py eklemeleri:**
```python
urlpatterns = [
    # ... mevcut URL'ler ...
    
    # Player API
    path('api/v1/courses/<uuid:course_id>/content/<uuid:content_id>/sessions/',
         include('backend.player.urls', namespace='player')),
    
    # Progress API
    path('api/v1/courses/<uuid:course_id>/content/<uuid:content_id>/progress/',
         include('backend.progress.urls', namespace='progress')),
    
    # Telemetry API
    path('api/v1/courses/<uuid:course_id>/content/<uuid:content_id>/events/',
         include('backend.telemetry.urls', namespace='telemetry')),
    
    # Sequencing API
    path('api/v1/courses/<uuid:course_id>/content/<uuid:content_id>/lock/',
         include('backend.sequencing.urls', namespace='sequencing')),
    
    # Quizzes API
    path('api/v1/quizzes/', include('backend.quizzes.urls', namespace='quizzes')),
]
```

---

## 🟡 PHASE 2 — MVP-2 (İnteraktif + AI-Assisted Learning)

> **Hedef:** Pasif izleyiciyi aktif öğrenene çevirmek

### 2.1 Timeline App (Interactive Overlay)
```markdown
backend/timeline/
├── __init__.py
├── apps.py
├── models.py           # TimelineNode
├── serializers.py
├── views.py            # TimelineViewSet
├── urls.py
└── tests/
```

**Modeller:**
```python
# TimelineNode
- id: UUID (PK)
- tenant_id: UUID
- course_id: UUID
- content_id: UUID
- node_type: TEXT (quiz|poll|checkpoint|hotspot|info)
- start_ts: INT
- end_ts: INT
- config: JSONB
- is_active: BOOLEAN
```

**TODO:**
- [ ] Timeline app oluştur
- [ ] TimelineNode modeli
- [ ] Timeline serializers
- [ ] TimelineViewSet (GET nodes for content)
- [ ] Admin endpoints (CRUD)
- [ ] URL'leri ekle
- [ ] Unit testler

### 2.2 Notes App (Timestamped Notes & Threads)
```markdown
backend/notes/
├── __init__.py
├── apps.py
├── models.py           # ContentNote, ContentThread, ThreadMessage, ContentHighlight
├── serializers.py
├── views.py
├── urls.py
└── tests/
```

**Modeller:**
```python
# ContentNote
# ContentThread
# ContentThreadMessage
# ContentHighlight
```

**TODO:**
- [ ] Notes app oluştur
- [ ] ContentNote, ContentThread, ThreadMessage, ContentHighlight modelleri
- [ ] Serializers
- [ ] ViewSets
- [ ] URL'ler
- [ ] Unit testler

### 2.3 AI App (Transcripts, RAG, Tutor)
```markdown
backend/ai/
├── __init__.py
├── apps.py
├── models.py           # AiArtifact, TranscriptSegment, AiConversation, AiMessage
├── serializers.py
├── views.py            # TranscriptViewSet, ChapterViewSet, AskViewSet
├── services/
│   ├── transcription.py    # ASR integration
│   ├── embedding.py        # Vector embedding
│   └── rag.py              # RAG Q&A
├── urls.py
└── tests/
```

**Modeller:**
```python
# AiArtifact
# TranscriptSegment
# AiConversation
# AiMessage
```

**Endpoints:**
```
GET  /api/v1/courses/{courseId}/content/{contentId}/ai/transcript
GET  /api/v1/courses/{courseId}/content/{contentId}/ai/chapters
GET  /api/v1/courses/{courseId}/content/{contentId}/ai/summary
POST /api/v1/courses/{courseId}/content/{contentId}/ai/ask
```

**TODO:**
- [ ] AI app oluştur
- [ ] Modeller
- [ ] ASR integration service
- [ ] Embedding service
- [ ] RAG service
- [ ] ViewSets
- [ ] URL'ler
- [ ] Celery tasks (transcript generation, embedding)
- [ ] Unit testler

---

## 🔵 PHASE 3 — SCALE (AI-Native LMS + Kurumsal)

### 3.1 Recommendations App
```markdown
backend/recommendations/
├── models.py           # LearningProfile, ContentRecommendation
├── services/
│   └── recommendation_engine.py
└── ...
```

**TODO:**
- [ ] Recommendations app oluştur
- [ ] LearningProfile modeli
- [ ] ContentRecommendation modeli
- [ ] Recommendation engine
- [ ] API endpoints

### 3.2 Integrity App
```markdown
backend/integrity/
├── models.py           # IntegritySignal
├── services/
│   └── anomaly_detector.py
└── ...
```

**TODO:**
- [ ] Integrity app oluştur
- [ ] IntegritySignal modeli
- [ ] Anomaly detection service
- [ ] Speed + seek + dwell analysis

---

## 📋 GELİŞTİRME SIRASI (Dependency Order)

```
1. libs/tenant_aware        → Tüm modeller buna bağımlı
2. libs/idempotency         → Progress/Telemetry buna bağımlı
3. player app               → Session başlatır
4. progress app             → Session'a bağımlı, policy tetikler
5. telemetry app            → Session'a bağımlı
6. sequencing app           → Progress'e bağımlı, quiz'i bekler
7. quizzes app              → Sequencing'i tetikler
8. timeline app             → Quiz ID'leri kullanır (MVP-2)
9. notes app                → Bağımsız (MVP-2)
10. ai app                  → En karmaşık, son (MVP-2)
```

---

## 🗄️ VERİTABANI MİGRASYON STRATEJİSİ

### Mevcut ContentProgress Durumu
`courses.ContentProgress` zaten var ve kullanımda. İki seçenek:

**Seçenek A: Genişletme (Tercih Edilen)**
- Mevcut ContentProgress'e yeni field'lar ekle
- Session FK ekle
- Migration ile güncelle

**Seçenek B: Yeni Model**
- `progress.EnhancedContentProgress` oluştur
- Data migration yap
- Eski modeli deprecate et

### Multi-Database Consideration
Mevcut ayarlarda 4 DB var:
- `default` → Player, Progress, Sequencing, Quizzes, Timeline, Notes
- `analytics` → Telemetry (yüksek yazma)
- `logs` → IntegritySignal
- `media` → AiArtifact

---

## ✅ KABUL KRİTERLERİ

### MVP-1 Çıkış Kriterleri
- [ ] Video izleniyor (signed URL ile)
- [ ] Session başlatılıyor ve heartbeat alınıyor
- [ ] İlerleme doğru ölçülüyor (seek ile watched_seconds artmıyor)
- [ ] Resume çalışıyor (cihaz değişse bile)
- [ ] Telemetry event'leri batch olarak alınıyor
- [ ] Min watch kuralı çalışıyor
- [ ] Önceki içerik tamamlanmadan sonraki açılmıyor
- [ ] Video içi quiz çalışıyor
- [ ] Quiz geçmeden ilerlenemiyor (policy)

### MVP-2 Çıkış Kriterleri
- [ ] Timeline node'ları render ediliyor
- [ ] Checkpoint'ler çalışıyor (devam için tıkla)
- [ ] Timestamped not alınabiliyor
- [ ] Soru sorulabiliyor (thread)
- [ ] Transkript görüntüleniyor
- [ ] AI ile soru sorulabiliyor
- [ ] Chapter'lar otomatik üretiliyor

---

## 🚀 BAŞLANGIÇ ADIMLARI

### Hemen Yapılacaklar
1. `backend/libs/` dizin yapısını oluştur
2. `TenantAwareModel` base class'ı yaz
3. `player` app'ini oluştur ve PlaybackSession modelini ekle
4. Settings ve URLs'e ekle
5. İlk migration'ı çalıştır
6. Basit API testleri yaz

### Sonraki Adımlar
- Progress app
- Telemetry app
- Diğer Phase 1 app'leri

---

## 📝 NOTLAR

- Tüm UUID'ler için `uuid.uuid4` kullanılacak
- Tenant isolation için `TenantAwareManager` kullanılacak
- Tüm write endpoint'leri `Idempotency-Key` destekleyecek
- API versiyonlama: `/api/v1/`
- Serializer'larda camelCase ↔ snake_case dönüşümü

