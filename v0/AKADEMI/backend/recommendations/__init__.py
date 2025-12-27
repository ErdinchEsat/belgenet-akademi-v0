"""
Recommendations App
===================

Kişiselleştirilmiş içerik önerileri.

Modeller:
- UserContentInterest: Kullanıcı içerik ilgi profili
- ContentSimilarity: İçerik benzerlik matrisi
- RecommendationLog: Öneri geçmişi

Endpoint'ler:
- GET /recommendations/           : Kişisel öneriler
- GET /recommendations/next/      : Sonraki içerik önerisi
- GET /recommendations/similar/   : Benzer içerikler
- GET /recommendations/trending/  : Trend içerikler
- POST /recommendations/feedback/ : Öneri geri bildirimi
"""

default_app_config = 'backend.recommendations.apps.RecommendationsConfig'

