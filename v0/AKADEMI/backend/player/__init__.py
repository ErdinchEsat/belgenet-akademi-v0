"""
Player App
==========

Video oynatıcı için playback session yönetimi.

Modeller:
- PlaybackSession: İzleme oturumu

Endpoint'ler:
- POST /sessions/: Oturum başlat
- PUT /sessions/{id}/heartbeat/: Heartbeat gönder
- PUT /sessions/{id}/end/: Oturumu sonlandır
"""

default_app_config = 'backend.player.apps.PlayerConfig'

