"""
Storage App
===========

Dosya yükleme ve depolama sistemi.

Özellikler:
- S3/MinIO uyumlu object storage
- Profil resmi yükleme
- Ödev dosyası yükleme
- Kurs materyalleri yükleme
- Dosya boyutu ve tip validasyonu
- Tenant-aware dosya yönetimi
"""

default_app_config = 'backend.storage.apps.StorageConfig'

