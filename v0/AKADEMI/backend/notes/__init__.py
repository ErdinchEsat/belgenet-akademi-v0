"""
Notes App
=========

Video üzerinde zamanlı notlar ve threads.

Modeller:
- VideoNote: Kullanıcının video üzerindeki notları
- NoteThread: Not altındaki tartışmalar
- NoteReply: Thread cevapları
- NoteReaction: Not reaksiyonları (like, bookmark)

Endpoint'ler:
- GET/POST /notes/         : Kullanıcının notlarını listele/oluştur
- GET/PUT/DELETE /notes/{id}/: Not detayı/güncelle/sil
- POST /notes/{id}/share/  : Notu paylaş
- GET/POST /notes/{id}/replies/: Thread cevapları
"""

default_app_config = 'backend.notes.apps.NotesConfig'

