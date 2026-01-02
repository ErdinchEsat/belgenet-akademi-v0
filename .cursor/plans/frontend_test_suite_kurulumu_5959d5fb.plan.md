---
name: Frontend Test Suite Kurulumu
overview: Akademi Istanbul Frontend (React 18 + TypeScript + Vite) icin Vitest + RTL + MSW tabanli kurumsal test altyapisi. Tum test dosyalari mayscon.v1/tests/akademi/frontend/ altinda. A0-A7 asamalari ile sistematik ilerleme, MVT ile hizli baslangic.
todos:
  - id: a0-deps
    content: "A0.1-A0.2: package.json bagimlilik ve scripts ekle"
    status: completed
  - id: a0-config
    content: "A0.3-A0.5: vitest.config.ts ve TypeScript ayarlari"
    status: completed
  - id: a1-setup
    content: "A1.1: setup.ts (jest-dom, MSW lifecycle, browser mocks)"
    status: completed
  - id: a1-utils
    content: "A1.2: test-utils.tsx (AllProviders, customRender)"
    status: completed
  - id: a1-factories
    content: "A1.3: factories/ (user, tenant, course)"
    status: completed
  - id: a1-msw
    content: "A1.4: mocks/ (server.ts, handlers/)"
    status: completed
  - id: a1-types
    content: "A1.5-A1.6: types.ts ve index.ts barrel export"
    status: completed
  - id: a2-button
    content: "A2.1 MVT: Button.test.tsx"
    status: completed
  - id: a2-header
    content: "A2.2 MVT: Header.test.tsx"
    status: completed
  - id: a3-auth
    content: "A3.1 MVT: AuthContext.test.tsx"
    status: completed
  - id: a3-hooks
    content: "A3.3 MVT: useApi.test.tsx (useCourses)"
    status: completed
  - id: a4-api
    content: "A4.1-A4.2 MVT: client.test.ts + auth.api.test.ts"
    status: completed
  - id: a5-form
    content: "A5.1 MVT: LoginForm.test.tsx"
    status: completed
  - id: readme
    content: README.md dokumantasyonu
    status: completed
---

# Frontend Unit Test Suite - Birlesmis Master Plan

> **Proje:** Akademi Istanbul Frontend (React 18 + TypeScript + Vite)> **Hedef:** Kurumsal standartlarda test suite (%80+ coverage)> **Test Konumu:** `mayscon.v1/tests/akademi/frontend/`> **Tahmini Sure:** 2-3 Hafta (MVP: 1 gun)---

## TESPIT EDILEN YAPI

| Ozellik | Deger ||---------|-------|| Frontend Root | `v0/AKADEMI/frontend/` || Package Manager | npm || Build Tool | Vite 6.2 || React | 18.2 || TypeScript | 5.8 || Path Alias | `@/*` -> `./*` || API Client | Axios (`lib/api/client.ts`) || Contexts | AuthContext, TenantContext || Hooks | useApi.ts (50+ hook), useWebSocket.ts || Components | 60+ (ui/, layout/, player/, features/) |---

## VARSAYIMLAR VE KARARLAR

| Karar | Secim | Gerekce ||-------|-------|---------|| Test Runner | **Vitest** | Vite ile native entegrasyon || Transform | esbuild | Vite default, hizli || Coverage | v8 | Vitest default, guvenilir || Router | MemoryRouter | Test izolasyonu icin || Query | role/label/text | data-testid son care |---

## KRITIK DUZELTMELER (Uygulama Oncesi)

> Bu bolumdeki sorunlar planda tespit edilmis ve cozumleri asagida belirtilmistir.

### Duzeltme 1: --config Yolu Hatali/Tasinamaz

**Sorun:** `--config ../MAYSCON/mayscon.v1/tests/akademi/frontend/vitest.config.ts` goreceli yol CI/CD ve farkli cwd'lerde kirilir.**Cozum:** `vitest.config.ts` dosyasini **frontend root**'a (`v0/AKADEMI/frontend/`) koy. Testler `mayscon.v1/tests/akademi/frontend/` altinda kalsin, config include ile onlari bulsun.

```json
{
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage",
  "test:ui": "vitest --ui"
}
```



### Duzeltme 2: frontendRoot Cozumu Yanlis

**Sorun:** `path.resolve(__dirname, '../../../../AKADEMI/frontend')` repo disina cikabilir veya yanlis path olusturabilir.**Cozum:** Config frontend root'ta oldugu icin `__dirname` zaten dogru yer. Test klasoru icin goreceli path kullan:

```typescript
// vitest.config.ts (v0/AKADEMI/frontend/ icinde)
const testDir = '../../MAYSCON/mayscon.v1/tests/akademi/frontend';

export default defineConfig({
  test: {
    include: [`${testDir}/specs/**/*.test.{ts,tsx}`],
    setupFiles: [`${testDir}/setup.ts`],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'), // frontend root
    },
  },
});
```



### Duzeltme 3: Alias Yanlis Set Edilirse Import Patlar

**Sorun:** `@` alias'i yanlis ayarlanirsa testlerdeki `import { Button } from '@/components/ui/Button'` patlar.**Cozum:**

- Alias `@` -> frontend root (`v0/AKADEMI/frontend/`)
- Test dosyalarinda import'lar `@/components/...` seklinde olacak
- `tsconfig.json` ile uyumlu olmali
```typescript
resolve: {
  alias: {
    '@': path.resolve(__dirname, '.'), // __dirname = v0/AKADEMI/frontend
  },
}
```




### Duzeltme 4: include Yanlis Dosyalari Yakalayabilir

**Sorun:** `include: ['**/*.test.{ts,tsx}']` tum repo'daki test dosyalarini yakalayabilir.**Cozum:** Tam path ile sadece frontend test klasorunu hedefle:

```typescript
include: [
  path.resolve(__dirname, '../../MAYSCON/mayscon.v1/tests/akademi/frontend/specs/**/*.test.{ts,tsx}')
],
exclude: [
  '**/node_modules/**',
  '**/dist/**',
  '**/backend/**',
]
```



### Duzeltme 5: Axios + MSW icin jsdom URL Seti

**Sorun:** jsdom'da `URL`, `URLSearchParams`, `TextEncoder`, `TextDecoder` eksik olabilir. MSW + Axios bu API'lara bagimli.**Cozum:** `setup.ts`'e global polyfill'ler ekle:

```typescript
// setup.ts
import { TextEncoder, TextDecoder } from 'util';

// jsdom URL polyfills
if (typeof globalThis.URL === 'undefined') {
  globalThis.URL = URL;
}
if (typeof globalThis.URLSearchParams === 'undefined') {
  globalThis.URLSearchParams = URLSearchParams;
}
if (typeof globalThis.TextEncoder === 'undefined') {
  globalThis.TextEncoder = TextEncoder;
}
if (typeof globalThis.TextDecoder === 'undefined') {
  globalThis.TextDecoder = TextDecoder as typeof globalThis.TextDecoder;
}

// Axios baseURL icin
if (typeof globalThis.location === 'undefined') {
  Object.defineProperty(globalThis, 'location', {
    value: { href: 'http://localhost:3000', origin: 'http://localhost:3000' },
    writable: true,
  });
}
```

---

## TEST KLASOR YAPISI

> **DUZELTME:** `vitest.config.ts` artik `v0/AKADEMI/frontend/` altinda (frontend root).> Test dosyalari ve yardimcilar `mayscon.v1/tests/akademi/frontend/` altinda kalir.

```javascript
v0/AKADEMI/frontend/
├── vitest.config.ts          # Config BURADA (Duzeltme 1-2)
└── ...

mayscon.v1/tests/akademi/frontend/
├── setup.ts                  # Global setup
├── test-utils.tsx            # Custom render
├── index.ts                  # Barrel export
├── types.ts                  # Test tipleri
├── README.md                 # Dokumantasyon
│
├── factories/
│   ├── index.ts
│   ├── user.factory.ts
│   ├── tenant.factory.ts
│   └── course.factory.ts
│
├── mocks/
│   ├── server.ts             # MSW server
│   └── handlers/
│       ├── index.ts
│       ├── auth.handlers.ts
│       ├── courses.handlers.ts
│       └── users.handlers.ts
│
└── specs/
    ├── components/           # A2 - Component testleri
    │   ├── Button.test.tsx
    │   ├── Header.test.tsx
    │   ├── Sidebar.test.tsx
    │   └── ...
    ├── contexts/             # A3 - Context testleri
    │   ├── AuthContext.test.tsx
    │   └── TenantContext.test.tsx
    ├── hooks/                # A3 - Hook testleri
    │   └── useApi.test.tsx
    ├── api/                  # A4 - API service testleri
    │   ├── client.test.ts
    │   └── auth.api.test.ts
    ├── forms/                # A5 - Form testleri
    │   └── LoginForm.test.tsx
    └── integration/          # A6 - Page testleri
        └── Dashboard.test.tsx
```

---

## A0 - KURULUM (P0 - Kritik) ~45 dk

### A0.1 Bagimliklarin Yuklenmesi

- **Amac:** Test kutuphanelerini yukle
- **Dosya:** `v0/AKADEMI/frontend/package.json`
- **Kabul:** `npm install` basarili
```bash
npm i -D vitest @vitest/ui @vitest/coverage-v8 jsdom
npm i -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm i -D msw@latest
```




### A0.2 Package.json Scripts

- **Amac:** Test komutlarini tanimla
- **Dosya:** `v0/AKADEMI/frontend/package.json`
- **Kabul:** `npm run test` calisir

> **DUZELTME 1 UYGULAMASI:** Config artik frontend root'ta, `--config` parametresi gereksiz.

```json
{
  "test": "vitest run",
  "test:watch": "vitest",
  "test:coverage": "vitest run --coverage",
  "test:ui": "vitest --ui"
}
```



### A0.3 Vitest Config

- **Amac:** Test ortami konfigurasyonu
- **Dosya:** `v0/AKADEMI/frontend/vitest.config.ts` **(DUZELTME: frontend root'a tasindi)**
- **Kabul:** jsdom ortami, path alias calisir, sadece frontend testleri yakalanir

> **DUZELTME 2-4 UYGULAMASI:** Tam config asagida:

```typescript
/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Test klasoru - goreceli path (Duzeltme 2)
const testDir = '../../MAYSCON/mayscon.v1/tests/akademi/frontend';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: [path.resolve(__dirname, testDir, 'setup.ts')],
    
    // DUZELTME 4: Sadece frontend test klasorunu hedefle
    include: [
      path.resolve(__dirname, testDir, 'specs/**/*.test.{ts,tsx}')
    ],
    exclude: ['**/node_modules/**', '**/dist/**', '**/backend/**'],
    
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportsDirectory: path.resolve(__dirname, testDir, 'coverage'),
      include: ['components/**', 'contexts/**', 'hooks/**', 'lib/**'],
      thresholds: { global: { statements: 70, branches: 65, functions: 70, lines: 70 } },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'), // DUZELTME 3: frontend root
    },
  },
});
```



### A0.4 TypeScript Ayarlari

- **Amac:** Test dosyalari icin tip destegi
- **Dosya:** tsconfig paths uyumu
- **Kabul:** Import hatalari yok

### A0.5 Git Ignore

- **Amac:** Coverage klasorlerini ignore et
- **Dosya:** `.gitignore`
- **Kabul:** `coverage/` ignore edilir

---

## A1 - TEST ALTYAPISI (P0 - Kritik) ~1.5 saat

### A1.1 Setup Dosyasi

- **Amac:** Global mock + jest-dom + MSW lifecycle
- **Dosya:** `mayscon.v1/tests/akademi/frontend/setup.ts`
- **Icerik:**
- `@testing-library/jest-dom` import
- afterEach cleanup
- MSW: beforeAll listen, afterEach reset, afterAll close
- Browser mocks: matchMedia, ResizeObserver, localStorage
- **DUZELTME 5:** jsdom URL/TextEncoder polyfill'leri

> **DUZELTME 5 UYGULAMASI:** Axios + MSW icin jsdom polyfill'leri:

```typescript
// setup.ts
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeAll, afterAll } from 'vitest';
import { server } from './mocks/server';
import { TextEncoder, TextDecoder } from 'util';

// ========== DUZELTME 5: jsdom URL Polyfills ==========
if (typeof globalThis.URL === 'undefined') {
  globalThis.URL = URL;
}
if (typeof globalThis.URLSearchParams === 'undefined') {
  globalThis.URLSearchParams = URLSearchParams;
}
if (typeof globalThis.TextEncoder === 'undefined') {
  globalThis.TextEncoder = TextEncoder;
}
if (typeof globalThis.TextDecoder === 'undefined') {
  globalThis.TextDecoder = TextDecoder as typeof globalThis.TextDecoder;
}

// Axios baseURL icin location mock
if (typeof globalThis.location === 'undefined') {
  Object.defineProperty(globalThis, 'location', {
    value: { href: 'http://localhost:3000', origin: 'http://localhost:3000' },
    writable: true,
  });
}

// ========== Browser API Mocks ==========
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// ========== MSW Lifecycle ==========
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
afterEach(() => {
  cleanup();
  server.resetHandlers();
});
afterAll(() => server.close());
```



### A1.2 Custom Render Utility

- **Amac:** Provider'larla sarili render
- **Dosya:** `tests/akademi/frontend/test-utils.tsx`
- **Icerik:**
- AllProviders (MemoryRouter, AuthProvider, TenantProvider)
- customRender(ui, options)
- userEvent.setup() pattern
- Re-export: screen, waitFor, within

### A1.3 Mock Data Factory

- **Amac:** Test verisi olusturma
- **Dosya:** `tests/akademi/frontend/factories/`
- **Icerik:**
- createMockUser(overrides)
- createMockTenant(overrides)
- createMockCourse(overrides)

### A1.4 MSW Handlers

- **Amac:** API mock'lari
- **Dosya:** `tests/akademi/frontend/mocks/`
- **Icerik:**
- server.ts (setupServer)
- auth.handlers.ts (login, me, logout, refresh)
- courses.handlers.ts (list, detail)
- users.handlers.ts (list, detail)

### A1.5 Type Definitions

- **Amac:** Test utility tipleri
- **Dosya:** `tests/akademi/frontend/types.ts`
- **Kabul:** RenderOptions, MockUser tipleri tanimli

### A1.6 Barrel Export

- **Amac:** Tek noktadan import
- **Dosya:** `tests/akademi/frontend/index.ts`
- **Kabul:** `import { render, createMockUser } from '../test'` calisir

---

## A2 - COMPONENT TESTLERI (P1 - Yuksek) ~3 saat

### A2.1 Button Component Test (MVT)

- **Dosya:** `specs/components/Button.test.tsx`
- **Testler:** render, click, disabled, loading, variants
- **Kabul:** 5+ test gecer

### A2.2 Header Component Test (MVT)

- **Dosya:** `specs/components/Header.test.tsx`
- **Testler:** user menu, auth state, logout click
- **Kabul:** 4+ test gecer

### A2.3 Sidebar Component Test

- **Dosya:** `specs/components/Sidebar.test.tsx`
- **Testler:** role-based menu items, active state
- **Kabul:** 3+ test gecer

### A2.4 Avatar Component Test

- **Dosya:** `specs/components/Avatar.test.tsx`
- **Testler:** image load, fallback, sizes
- **Kabul:** 3+ test gecer

### A2.5 GenericTable Component Test

- **Dosya:** `specs/components/GenericTable.test.tsx`
- **Testler:** empty state, data render, sorting
- **Kabul:** 4+ test gecer

### A2.6 UniversalCourseCard Test

- **Dosya:** `specs/components/UniversalCourseCard.test.tsx`
- **Testler:** progress bar, instructor info, CTA
- **Kabul:** 3+ test gecer

---

## A3 - HOOK/CONTEXT TESTLERI (P1 - Yuksek) ~2 saat

### A3.1 AuthContext Test (MVT)

- **Dosya:** `specs/contexts/AuthContext.test.tsx`
- **Testler:**
- login sets user
- logout clears user
- isAuthenticated dogru
- error state
- **Kabul:** 5+ test gecer

### A3.2 TenantContext Test

- **Dosya:** `specs/contexts/TenantContext.test.tsx`
- **Testler:** currentTenant, switchTenant
- **Kabul:** 3+ test gecer

### A3.3 useCourses Hook Test (MVT)

- **Dosya:** `specs/hooks/useApi.test.tsx`
- **Testler:**
- loading -> success
- error state
- refetch
- **Kabul:** 4+ test gecer

### A3.4 useUsers Hook Test

- **Dosya:** `specs/hooks/useApi.test.tsx` (ayni dosya)
- **Testler:** pagination, filter
- **Kabul:** 3+ test gecer

---

## A4 - API SERVICE TESTLERI (P1 - Yuksek) ~1.5 saat

### A4.1 API Client Test (MVT)

- **Dosya:** `specs/api/client.test.ts`
- **Testler:**
- token injection header
- 401 error handling
- error parsing
- **Kabul:** 4+ test gecer

### A4.2 Auth API Test (MVT)

- **Dosya:** `specs/api/auth.api.test.ts`
- **Testler:**
- login success (token stored)
- login error (401)
- logout (token cleared)
- getCurrentUser
- **Kabul:** 5+ test gecer

### A4.3 Courses API Test

- **Dosya:** `specs/api/courses.api.test.ts`
- **Testler:** list, getById, enroll
- **Kabul:** 4+ test gecer

---

## A5 - FORM VALIDATION TESTLERI (P2 - Orta) ~1 saat

### A5.1 Login Form Test (MVT)

- **Dosya:** `specs/forms/LoginForm.test.tsx`
- **Testler:**
- email required
- invalid email format
- password required
- submit disabled/enabled
- error display
- **Kabul:** 5+ test gecer

### A5.2 Profile Form Test

- **Dosya:** `specs/forms/ProfileForm.test.tsx`
- **Testler:** field validation, save
- **Kabul:** 3+ test gecer

---

## A6 - INTEGRATION TESTLERI (P2 - Orta) ~1.5 saat

### A6.1 Student Dashboard Test

- **Dosya:** `specs/integration/StudentDashboard.test.tsx`
- **Testler:** data load, stats display
- **Kabul:** 3+ test gecer

### A6.2 Login Flow Test

- **Dosya:** `specs/integration/LoginFlow.test.tsx`
- **Testler:** login -> redirect
- **Kabul:** 2+ test gecer

---

## A7 - CI/QUALITY GATE (P1 - Yuksek) ~30 dk

### A7.1 Coverage Threshold

- **Dosya:** `vitest.config.ts`
- **Deger:** Global %70, kritik klasorler %80
- **Kabul:** CI'da coverage check gecer

### A7.2 Pre-commit Hook (Opsiyonel)

- **Dosya:** `.husky/pre-commit`
- **Kabul:** Commit oncesi test calisir

### A7.3 GitHub Actions (Opsiyonel)

- **Dosya:** `.github/workflows/frontend-tests.yml`
- **Kabul:** PR'larda otomatik test

---

## MVT - MINIMUM VIABLE TEST SUITE (Ilk Gun)

**Hedef:** 4-5 saatte tamamlanacak en kucuk calisir set| # | Gorev | Dosya | Sure ||---|-------|-------|------|| 1 | Bagimlik yukle | package.json | 10 dk || 2 | Vitest config | vitest.config.ts | 15 dk || 3 | Setup dosyasi | setup.ts | 20 dk || 4 | Custom render | test-utils.tsx | 30 dk || 5 | Factories | factories/*.ts | 20 dk || 6 | MSW handlers | mocks/*.ts | 30 dk || 7 | Button test | Button.test.tsx | 20 dk || 8 | Header test | Header.test.tsx | 25 dk || 9 | AuthContext test | AuthContext.test.tsx | 30 dk || 10 | Auth API test | auth.api.test.ts | 30 dk || 11 | useApi test | useApi.test.tsx | 30 dk || 12 | Login form test | LoginForm.test.tsx | 30 dk || 13 | README | README.md | 15 dk |**Toplam MVT:** ~4.5 saat---

## ONCELIK MATRISI

| Oncelik | Asama | Gorev | Sure ||---------|-------|-------|------|| P0 | A0 + A1 | Kurulum + Altyapi | 2 saat || P1 | A2-A4, A7 | Component/Hook/API + CI | 6-7 saat || P2 | A5-A6 | Form/Integration | 2.5 saat || **Toplam** | | | **10-12 saat** |---

## KABUL KRITERLERI

1. `cd v0/AKADEMI/frontend && npm run test` basarili
2. MVT (6 test dosyasi) yesil
3. MSW unhandled request error veriyor
4. Coverage raporu olusturuluyor (%70+)
5. `npm run test:ui` Vitest UI aciliyor
6. README dokumantasyonu tamam