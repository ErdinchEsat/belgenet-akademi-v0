# 📋 BelgeNet Konsolidasyon İş Programı

**Tarih:** 27 Aralık 2024  
**Versiyon:** 1.0

---

## 🎯 HEDEFLER

1. ✅ Frontend React korunacak (değiştirilmeyecek)
2. ❌ SQLite3 veritabanı kaldırılacak
3. 🔄 Menu yapısı MAYSCON tools/menu altına taşınacak
4. 🗑️ Mükerrer yapılar temizlenecek
5. ⚙️ Ayarlar konsolide edilecek

---

## 📝 YAPILACAKLAR LİSTESİ (SIRALI)

### AŞAMA 1: TEMİZLİK İŞLEMLERİ

| # | Görev | Açıklama | Dosya/Dizin | Eylem |
|---|-------|----------|-------------|-------|
| **1.1** | Sanal ortam kaldır | Akademi'nin ayrı venv'i gereksiz | `v0/AKADEMI/venv/` | 🗑️ SİL |
| **1.2** | SQLite kaldır | PostgreSQL kullanılacak | `v0/AKADEMI/db.sqlite3` | 🗑️ SİL |
| **1.3** | Boş static kaldır | MAYSCON webapp kullanılacak | `v0/AKADEMI/static/` | 🗑️ SİL |
| **1.4** | Boş media kaldır | MAYSCON webapp kullanılacak | `v0/AKADEMI/media/` | 🗑️ SİL |
| **1.5** | Boş templates kaldır | MAYSCON webapp kullanılacak | `v0/AKADEMI/templates/` | 🗑️ SİL |
| **1.6** | env.example kaldır | MAYSCON infra/env kullanılacak | `v0/AKADEMI/env.example` | 🗑️ SİL |

### AŞAMA 2: LOG TAŞIMA

| # | Görev | Açıklama | Eylem |
|---|-------|----------|-------|
| **2.1** | Log dizini oluştur | Akademi logları için alt klasör | `mayscon.v1/logs/data/akademi/` oluştur |
| **2.2** | Logları taşı | Akademi loglarını taşı | `AKADEMI/logs/data/*` → `mayscon.v1/logs/data/akademi/` |
| **2.3** | Eski log dizini kaldır | Boş kalan dizini temizle | `v0/AKADEMI/logs/` sil |

### AŞAMA 3: MENU YAPISI DÜZENLEMESİ

| # | Görev | Açıklama | Eylem |
|---|-------|----------|-------|
| **3.1** | Menu klasör yapısı | Proje bazlı menu yapısı | `mayscon.v1/tools/menu/` düzenle |
| **3.2** | Ortak modül | Paylaşılan fonksiyonlar | `menu/common.ps1` oluştur |
| **3.3** | MAYSCON menu | MAYSCON'a özel komutlar | `menu/mayscon/` klasörü |
| **3.4** | Akademi menu | Akademi'ye özel komutlar | `menu/akademi/` klasörü |
| **3.5** | Ana launcher | Proje seçici ana menu | `menu/launcher.ps1` oluştur |
| **3.6** | Eski menu kaldır | AKADEMI menu dizini | `v0/AKADEMI/menu/` sil |

### AŞAMA 4: AYAR GÜNCELLEMELERİ

| # | Görev | Açıklama | Dosya |
|---|-------|----------|-------|
| **4.1** | SQLite fallback kaldır | PostgreSQL zorunlu | `akademi/settings.py` |
| **4.2** | Static/Media güncelle | MAYSCON'a yönlendir | `akademi/settings.py` |
| **4.3** | Templates güncelle | MAYSCON'a yönlendir | `akademi/settings.py` |
| **4.4** | Logging güncelle | Yeni log yolu | `akademi/settings.py` |

### AŞAMA 5: REQUIREMENTS GÜNCELLEMESİ

| # | Görev | Açıklama | Dosya |
|---|-------|----------|-------|
| **5.1** | Akademi paketleri ekle | Eksik paketler | `tools/requirements/api.txt` |
| **5.2** | Full requirements | Tüm bağımlılıklar | `tools/requirements/full.txt` |

### AŞAMA 6: TEST VE DOĞRULAMA

| # | Görev | Açıklama |
|---|-------|----------|
| **6.1** | Django check | `python manage.py check` |
| **6.2** | Migration kontrolü | `python manage.py showmigrations` |
| **6.3** | Sunucu testi | `python manage.py runserver` |
| **6.4** | Menu testi | Yeni menu yapısını test et |

---

## 🗂️ YENİ MENU YAPISI

```
mayscon.v1/tools/menu/
├── __init__.py
├── launcher.ps1              # Ana başlatıcı (proje seçici)
├── launcher.bat              # Windows batch wrapper
│
├── common/                   # Paylaşılan modüller
│   ├── __init__.py
│   ├── colors.ps1            # Renk tanımları
│   ├── helpers.ps1           # Yardımcı fonksiyonlar
│   └── banner.ps1            # Banner çizimi
│
├── mayscon/                  # MAYSCON'a özel
│   ├── menu.ps1              # Ana menu
│   ├── commands.ps1          # Komut tanımları
│   └── docker.ps1            # Docker komutları
│
└── akademi/                  # Akademi'ye özel
    ├── menu.ps1              # Ana menu
    ├── commands.ps1          # Komut tanımları
    ├── backend.ps1           # Django komutları
    └── frontend.ps1          # React/Vite komutları
```

### Ortak Komutlar (Her iki projede de olan)
- Docker işlemleri
- Database işlemleri
- Log izleme
- Backup

### MAYSCON'a Özel
- Core init/update/sync
- Webapp yönetimi
- Merkezi monitor

### Akademi'ye Özel
- Django migration/shell
- Frontend (npm) komutları
- Test data oluşturma
- API testing

---

## 📊 TAHMİNİ SÜRE

| Aşama | Süre |
|-------|------|
| Aşama 1: Temizlik | ~15 dk |
| Aşama 2: Log taşıma | ~10 dk |
| Aşama 3: Menu yapısı | ~45 dk |
| Aşama 4: Ayar güncelleme | ~30 dk |
| Aşama 5: Requirements | ~10 dk |
| Aşama 6: Test | ~15 dk |
| **TOPLAM** | **~2 saat** |

---

## ⚠️ DİKKAT EDİLECEKLER

1. **Frontend'e dokunma!** React kodu korunacak.
2. **mayscon.venv kullan!** Akademi için ayrı venv yok.
3. **PostgreSQL zorunlu!** SQLite fallback kaldırılacak.
4. **Log dosyaları kaybolmasın!** Taşımadan önce yedekle.

---

## ✅ BAŞLAMA ONAY

Bu iş programı onaylandıktan sonra sırayla uygulanacaktır.

**Başlamak için onay verin.**

