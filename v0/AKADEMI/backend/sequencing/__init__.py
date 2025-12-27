"""
Sequencing App
==============

İçerik kilitleme ve sıralı öğrenme için policy engine.

Modeller:
- ContentLockPolicy: Kilit kuralları
- ContentUnlockState: Kullanıcı bazlı kilit durumu

Endpoint'ler:
- GET  /lock/: Kilit durumu sorgula
- POST /lock/evaluate/: Kilit değerlendir
"""

default_app_config = 'backend.sequencing.apps.SequencingConfig'

