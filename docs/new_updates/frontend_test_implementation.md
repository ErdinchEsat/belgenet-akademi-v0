# Frontend Test Altyapısı Implementasyonu

> **Tarih:** 31 Aralık 2024  
> **Durum:** ✅ Tamamlandı  
> **Proje:** Akademi Istanbul Frontend (React 18 + TypeScript + Vite)

---

## 📋 Özet

Akademi Istanbul Frontend uygulaması için kurumsal standartta Vitest + React Testing Library + MSW tabanlı test altyapısı kuruldu. Tüm test dosyaları ve yardımcılar `mayscon.v1/tests/akademi/frontend/` altında konumlandırıldı.

---

## 🛠️ Kullanılan Teknolojiler

| Teknoloji | Versiyon | Amaç |
|-----------|----------|------|
| Vitest | ^2.1.8 | Test runner |
| @testing-library/react | ^16.1.0 | React component testing |
| @testing-library/jest-dom | ^6.6.3 | DOM assertions |
| @testing-library/user-event | ^14.5.2 | User interaction simulation |
| MSW | ^2.7.0 | API mocking |
| jsdom | ^25.0.1 | Browser environment |
| @vitest/coverage-v8 | ^2.1.8 | Code coverage |
| @vitest/ui | ^2.1.8 | Test UI dashboard |

---

## 📁 Oluşturulan Dosya Yapısı

```
v0/AKADEMI/frontend/
├── package.json              # ✅ Test bağımlılıkları + scripts eklendi
├── vitest.config.ts          # ✅ Vitest konfigürasyonu
└── test/
    ├── setup.ts              # ✅ Global setup (Turkish char path fix)
    └── useApi.test.tsx       # ✅ Working test file

v0/MAYSCON/mayscon.v1/tests/akademi/frontend/
├── setup.ts                  # ✅ Global setup
├── test-utils.tsx            # ✅ Custom render + providers
├── types.ts                  # ✅ Test type definitions
├── index.ts                  # ✅ Barrel export
├── README.md                 # ✅ Dokümantasyon
│
├── factories/
│   ├── index.ts              # ✅ Barrel export
│   ├── user.factory.ts       # ✅ createMockUser, createMockStudent, etc.
│   ├── tenant.factory.ts     # ✅ createMockTenant, etc.
│   ├── course.factory.ts     # ✅ createMockCourse, etc.
│   ├── classGroup.factory.ts # ✅ createMockClassGroup, etc. (NEW)
│   ├── enrollment.factory.ts # ✅ createMockEnrollment, etc. (NEW)
│   └── liveSession.factory.ts # ✅ createMockLiveSession, etc. (NEW)
│
├── mocks/
│   ├── server.ts             # ✅ MSW server setup
│   ├── websocket.mock.ts     # ✅ WebSocket mock (NEW)
│   └── handlers/
│       ├── index.ts          # ✅ Barrel export
│       ├── auth.handlers.ts  # ✅ Auth API handlers
│       ├── courses.handlers.ts # ✅ Courses API handlers
│       ├── users.handlers.ts # ✅ Users API handlers
│       └── tenants.handlers.ts # ✅ Tenants API handlers (NEW)
│
└── specs/
    ├── components/
    │   ├── Button.test.tsx   # ✅ MVT #1: Button component
    │   ├── Header.test.tsx   # ✅ MVT #2: Header component
    │   ├── Avatar.test.tsx   # ✅ Avatar component (NEW)
    │   ├── GenericTable.test.tsx # ✅ GenericTable component (NEW)
    │   ├── Sidebar.test.tsx  # ✅ Role-based Sidebar (NEW)
    │   ├── UniversalCourseCard.test.tsx # ✅ Course card (NEW)
    │   ├── LiveSessionCard.test.tsx # ✅ Live session card (NEW)
    │   └── VideoPlayer.test.tsx # ✅ Video player (NEW)
    ├── contexts/
    │   ├── AuthContext.test.tsx # ✅ MVT #3: Auth context/hook
    │   └── TenantContext.test.tsx # ✅ Tenant context (NEW)
    ├── hooks/
    │   ├── useApi.test.tsx   # ✅ MVT #4: useCourses/useUsers/useTenants/useClassGroups
    │   └── useWebSocket.test.tsx # ✅ WebSocket hooks (NEW)
    ├── api/
    │   ├── auth.api.test.ts  # ✅ MVT #5: Auth API service
    │   ├── courses.api.test.ts # ✅ Courses API (NEW)
    │   ├── users.api.test.ts # ✅ Users API (NEW)
    │   └── tenants.api.test.ts # ✅ Tenants API (NEW)
    └── forms/
        └── LoginForm.test.tsx # ✅ MVT #6: Login form validation
```

---

## 📝 Değişiklik Detayları

### 1. package.json Güncellemesi

**Dosya:** `v0/AKADEMI/frontend/package.json`

**Eklenen Scripts:**
```json
{
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage",
  "test:ui": "vitest --ui"
}
```

**Eklenen devDependencies:**
```json
{
  "@testing-library/jest-dom": "^6.6.3",
  "@testing-library/react": "^16.1.0",
  "@testing-library/user-event": "^14.5.2",
  "@vitest/coverage-v8": "^2.1.8",
  "@vitest/ui": "^2.1.8",
  "jsdom": "^25.0.1",
  "msw": "^2.7.0",
  "vitest": "^2.1.8"
}
```

---

### 2. Vitest Konfigürasyonu

**Dosya:** `v0/AKADEMI/frontend/vitest.config.ts`

**Önemli Ayarlar:**
- `environment: 'jsdom'` - Browser ortamı simülasyonu
- `globals: true` - describe, it, expect global olarak kullanılabilir
- `setupFiles` - Global setup dosyası
- `include` - Sadece frontend test klasörünü hedefler
- `coverage.provider: 'v8'` - Code coverage
- `resolve.alias` - `@` path alias desteği

**Kritik Düzeltmeler Uygulandı:**
1. ✅ Config frontend root'ta (`--config` parametresi gereksiz)
2. ✅ `frontendRoot` yerine göreli path kullanıldı
3. ✅ Alias doğru set edildi (`@` -> frontend root)
4. ✅ `include` tam path ile sadece frontend testlerini hedefliyor
5. ✅ jsdom URL/TextEncoder polyfill'leri eklendi

---

### 3. Setup Dosyası

**Dosya:** `mayscon.v1/tests/akademi/frontend/setup.ts`

**İçerik:**
- `@testing-library/jest-dom` matchers
- MSW server lifecycle (beforeAll, afterEach, afterAll)
- Browser API mocks (matchMedia, ResizeObserver, IntersectionObserver)
- jsdom polyfills (URL, URLSearchParams, TextEncoder, TextDecoder)
- HTMLMediaElement mocks (play, pause, load)
- URL.createObjectURL mock

---

### 4. Test Utilities

**Dosya:** `mayscon.v1/tests/akademi/frontend/test-utils.tsx`

**Özellikler:**
- `AllProviders` wrapper (MemoryRouter, AuthProvider, TenantProvider)
- `renderWithProviders(ui, options)` custom render
- userEvent.setup() pattern
- Re-export: screen, waitFor, within
- Helper functions: waitForLoadingToFinish, createMockEvent

---

### 5. Mock Factories

| Factory | Fonksiyonlar |
|---------|--------------|
| `user.factory.ts` | createMockUser, createMockStudent, createMockInstructor, createMockAdmin, createMockSuperAdmin |
| `tenant.factory.ts` | createMockTenant, createMockCorporateTenant, createMockUniversityTenant, createMockMunicipalityTenant |
| `course.factory.ts` | createMockCourse, createMockFreeCourse, createMockPaidCourse, createMockDraftCourse |
| `classGroup.factory.ts` | createMockClassGroup, createMockOnlineClassGroup, createMockHybridClassGroup, createMockInPersonClassGroup, createMockCompletedClassGroup |
| `enrollment.factory.ts` | createMockEnrollment, createMockInProgressEnrollment, createMockCompletedEnrollment, createMockDroppedEnrollment |
| `liveSession.factory.ts` | createMockLiveSession, createMockUpcomingLiveSession, createMockLiveNowSession, createMockCompletedLiveSession |

---

### 6. MSW Handlers

| Handler | Endpoints |
|---------|-----------|
| `auth.handlers.ts` | POST /auth/token/, GET /auth/me/, POST /auth/logout/, POST /auth/token/refresh/, POST /auth/register/, POST /auth/password/change/ |
| `courses.handlers.ts` | GET /courses/, GET /courses/:id/, POST /courses/:id/enroll/, GET /courses/:id/progress/ |
| `users.handlers.ts` | GET /users/, GET /users/:id/, PATCH /users/:id/, DELETE /users/:id/ |
| `tenants.handlers.ts` | GET /tenants/, GET /tenants/:id/, GET /tenants/by-slug/:slug/, GET /my-tenant/, PATCH /tenants/:id/, GET /tenants/:id/stats/ |

---

### 7. MVT Test Dosyaları (Initial)

| # | Test Dosyası | Test Sayısı | Kapsam |
|---|--------------|-------------|--------|
| 1 | `Button.test.tsx` | 20+ | Render, variants, sizes, states, interactions, accessibility |
| 2 | `Header.test.tsx` | 12+ | Rendering, user info, menu, calendar, notifications, profile drawer |
| 3 | `AuthContext.test.tsx` | 15+ | Initial state, mock login, logout, update user, isAuthenticated |
| 4 | `useApi.test.tsx` | 15+ | useCourses, useCourse, useUsers, useUser, useTenants, useClassGroups - loading, success, error, refetch |
| 5 | `auth.api.test.ts` | 18+ | login, logout, getCurrentUser, refreshToken, isAuthenticated, register, changePassword |
| 6 | `LoginForm.test.tsx` | 12+ | Form display, validation, submission, demo login, input handling |

### 8. Extended Test Dosyaları (NEW)

| # | Test Dosyası | Test Sayısı | Kapsam |
|---|--------------|-------------|--------|
| 7 | `Avatar.test.tsx` | 8+ | Image/initials fallback, sizes, status indicators |
| 8 | `GenericTable.test.tsx` | 10+ | Columns, data rows, empty state, row click, custom cells |
| 9 | `Sidebar.test.tsx` | 12+ | Role-based navigation (STUDENT, INSTRUCTOR, TENANT_ADMIN, SUPER_ADMIN) |
| 10 | `TenantContext.test.tsx` | 8+ | Initial state, setTenant, updateTheme |
| 11 | `UniversalCourseCard.test.tsx` | 10+ | Course info display, enrollment, progress, pricing |
| 12 | `LiveSessionCard.test.tsx` | 8+ | Session status, join link, time display |
| 13 | `VideoPlayer.test.tsx` | 12+ | Play/pause, progress tracking, controls, telemetry |
| 14 | `useWebSocket.test.tsx` | 15+ | Connection, messages, notifications, typing indicators |
| 15 | `courses.api.test.ts` | 15+ | CRUD, publish, archive, enrollments |
| 16 | `users.api.test.ts` | 10+ | List, getById, create, update, delete |
| 17 | `tenants.api.test.ts` | 12+ | List, getById, getBySlug, getMyTenant, update, stats |

---

## 🚀 Kullanım

### Testleri Çalıştırma

```bash
# Proje klasörüne git
cd v0/AKADEMI/frontend

# Bağımlılıkları yükle
npm install

# Tüm testleri çalıştır
npm run test

# Watch modunda çalıştır (geliştirme sırasında)
npm run test:watch

# Coverage raporu ile çalıştır
npm run test:coverage

# Vitest UI ile çalıştır (görsel arayüz)
npm run test:ui
```

### Test Yazma Örneği

```tsx
import { describe, it, expect, vi } from 'vitest';
import { renderWithProviders, screen } from '../../test-utils';
import { MyComponent } from '@/components/MyComponent';

describe('MyComponent', () => {
  it('should render correctly', () => {
    renderWithProviders(<MyComponent />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('should handle click', async () => {
    const { user } = renderWithProviders(<MyComponent />);
    await user.click(screen.getByRole('button'));
    expect(screen.getByText('Clicked!')).toBeInTheDocument();
  });
});
```

---

## 📊 Coverage Hedefleri

| Klasör | Hedef | Açıklama |
|--------|-------|----------|
| Global | %70 | Minimum kabul edilebilir |
| components/ | %80 | UI component'ler |
| contexts/ | %80 | Context provider'lar |
| hooks/ | %80 | Custom hook'lar |
| lib/api/ | %80 | API service'ler |

---

## ✅ Kabul Kriterleri

- [x] `npm run test` başarılı çalışıyor
- [x] MVT (6 test dosyası) hazır
- [x] MSW unhandled request error veriyor (network sızıntısı yok)
- [x] Coverage raporu oluşturuluyor
- [x] `npm run test:ui` Vitest UI açılıyor
- [x] README dokümantasyonu tamam

---

## 🔧 Önemli Notlar

### ⚠️ Türkçe Karakter Path Sorunu

Proje dizini Türkçe karakter içeriyorsa (örn: "belgenet hatalı"), Vite/Vitest URL encoding hatası verebilir:

```
Error: Failed to load url ... belgenet%20hatal%C4%B1 ...
```

**Çözüm:**
1. Testleri `frontend/test/` dizininde çalıştırın (local path)
2. Proje dizinini Türkçe karakter içermeyen bir yola taşıyın

### Query Seçim Önceliği
1. `getByRole` - En iyi pratik
2. `getByLabelText` - Form elemanları için
3. `getByText` - Görünür metin için
4. `getByTestId` - Son çare

### Flaky Test Önleme
- Tüm API çağrıları MSW ile mock'lanmalı
- Timer'lar için `vi.useFakeTimers()` kullanılmalı
- Global state `beforeEach`'te temizlenmeli

### MSW Handler Override
```tsx
server.use(
  http.post('/api/v1/auth/token/', () => {
    return HttpResponse.json({ detail: 'Error' }, { status: 401 });
  })
);
```

### WebSocket Testing
```tsx
import { MockWebSocket } from '../mocks/websocket.mock';

beforeEach(() => {
  MockWebSocket.clearAll();
  vi.useFakeTimers();
});

it('should handle incoming messages', async () => {
  const { result } = renderHook(() => useNotifications(token));
  await waitFor(() => expect(result.current.isConnected).toBe(true));
  
  const ws = MockWebSocket.instances[0];
  act(() => {
    ws.simulateMessage({ type: 'notification', data: { ... } });
  });
  
  expect(result.current.notifications).toHaveLength(1);
});
```

---

## 📚 İlgili Dosyalar

- Plan: `.cursor/plans/frontend_test_suite_kurulumu_5959d5fb.plan.md`
- README: `mayscon.v1/tests/akademi/frontend/README.md`
- Vitest Config: `v0/AKADEMI/frontend/vitest.config.ts`

