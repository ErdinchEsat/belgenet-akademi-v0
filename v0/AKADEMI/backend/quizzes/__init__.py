"""
Quizzes App
===========

Video içi ve standalone quiz sistemi.

Modeller:
- Quiz: Quiz tanımı
- QuizQuestion: Quiz soruları
- QuizAttempt: Quiz denemesi
- QuizAnswer: Quiz cevapları

Endpoint'ler:
- GET  /quizzes/{id}/: Quiz detayı
- POST /quizzes/{id}/attempts/: Quiz başlat
- POST /quizzes/{id}/attempts/{attemptId}/submit: Quiz gönder
"""

default_app_config = 'backend.quizzes.apps.QuizzesConfig'

