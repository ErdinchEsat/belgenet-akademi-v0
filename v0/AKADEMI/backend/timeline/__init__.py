"""
Timeline App
============

Video üzerinde interaktif overlay engine.

Modeller:
- TimelineNode: Video üzerindeki etkileşim noktaları

Node Türleri:
- quiz: Video içi quiz
- poll: Anket
- checkpoint: İlerleme kontrol noktası
- hotspot: Tıklanabilir bölge
- info: Bilgi kartı

Endpoint'ler:
- GET /timeline/: İçerik için timeline node'larını getir
"""

default_app_config = 'backend.timeline.apps.TimelineConfig'

