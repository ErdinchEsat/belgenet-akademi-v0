"""
AI App
======

Video tabanlı AI özellikleri.

Modeller:
- Transcript: Video transkriptleri (SRT, VTT)
- TranscriptSegment: Transkript segmentleri
- AIConversation: AI tutor konuşmaları
- AIMessage: Konuşma mesajları
- VideoSummary: AI tarafından oluşturulan özetler

Endpoint'ler:
- GET /transcript/       : Video transkriptini getir
- GET /transcript/search/: Transkriptte arama
- POST /ai/ask/          : AI'a soru sor
- GET /ai/conversations/ : Konuşma geçmişi
- POST /ai/summarize/    : Özet oluştur
"""

default_app_config = 'backend.ai.apps.AIConfig'

