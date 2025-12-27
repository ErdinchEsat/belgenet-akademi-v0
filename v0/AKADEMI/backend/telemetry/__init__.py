"""
Telemetry App
=============

Video oynatıcı event tracking ve analytics.

Modeller:
- TelemetryEvent: Oynatıcı olayları (play, pause, seek, etc.)

Endpoint'ler:
- POST /events/: Batch event ingestion
"""

default_app_config = 'backend.telemetry.apps.TelemetryConfig'

