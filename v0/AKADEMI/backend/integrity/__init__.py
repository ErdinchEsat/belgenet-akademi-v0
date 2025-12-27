"""
Integrity App
=============

Video oynatma bütünlüğü ve güvenlik kontrolü.

Modeller:
- IntegrityCheck: Bütünlük kontrol kaydı
- AnomalyLog: Anomali tespiti
- DeviceFingerprint: Cihaz parmak izi
- PlaybackAnomaly: Oynatma anomalileri

Endpoint'ler:
- POST /integrity/verify/     : Playback bütünlük doğrulama
- GET /integrity/status/      : Kullanıcı bütünlük durumu
- POST /integrity/report/     : Anomali raporu

Özellikler:
- Tab visibility tracking
- Playback speed anomaly detection
- Seek pattern analysis
- Multi-device detection
- Session hijacking prevention
"""

default_app_config = 'backend.integrity.apps.IntegrityConfig'

