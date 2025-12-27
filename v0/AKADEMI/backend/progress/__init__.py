"""
Progress App
============

Video ilerleme takibi için gelişmiş modüller.

Modeller:
- ContentProgress: İçerik ilerleme durumu (mevcut model'i genişletir)
- ProgressWatchWindow: İzleme penceresi doğrulama

Endpoint'ler:
- GET  /progress/: İlerleme durumu
- PUT  /progress/: İlerleme güncelle
"""

default_app_config = 'backend.progress.apps.ProgressConfig'

