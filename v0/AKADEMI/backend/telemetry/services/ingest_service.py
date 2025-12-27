"""
Ingest Service
==============

Event batch ingestion ve dedupe.
"""

import logging
from typing import List, Dict, Tuple
from django.db import IntegrityError
from django.utils import timezone

from backend.player.models import PlaybackSession
from ..models import TelemetryEvent

logger = logging.getLogger(__name__)


class IngestService:
    """
    Telemetry event ingestion servisi.
    
    Sorumluluklar:
    - Batch event ingestion
    - Dedupe (client_event_id bazlı)
    - Event doğrulama
    - Bulk insert optimizasyonu
    """
    
    @classmethod
    def ingest_batch(
        cls,
        session: PlaybackSession,
        events: List[Dict],
    ) -> Tuple[int, int, int, List[Dict]]:
        """
        Event batch'ini işle.
        
        Args:
            session: Aktif playback session
            events: Event listesi
        
        Returns:
            Tuple[accepted, deduped, rejected, errors]
        """
        accepted = 0
        deduped = 0
        rejected = 0
        errors = []
        
        # Mevcut client_event_id'leri kontrol et (dedupe)
        existing_ids = set(
            TelemetryEvent.objects.filter(
                session=session,
                client_event_id__in=[e['client_event_id'] for e in events]
            ).values_list('client_event_id', flat=True)
        )
        
        # Event objelerini hazırla
        events_to_create = []
        
        for event_data in events:
            client_event_id = event_data['client_event_id']
            
            # Dedupe kontrolü
            if client_event_id in existing_ids:
                deduped += 1
                continue
            
            try:
                event = TelemetryEvent(
                    tenant=session.tenant,
                    session=session,
                    user=session.user,
                    course=session.course,
                    content=session.content,
                    client_event_id=client_event_id,
                    event_type=event_data['event_type'],
                    video_ts=event_data.get('video_ts'),
                    server_ts=timezone.now(),
                    client_ts=event_data.get('client_ts'),
                    payload=event_data.get('payload'),
                )
                events_to_create.append(event)
                existing_ids.add(client_event_id)  # Batch içi dedupe
                
            except Exception as e:
                rejected += 1
                errors.append({
                    'client_event_id': client_event_id,
                    'error': str(e),
                })
                logger.warning(f"Event validation failed: {client_event_id}, {e}")
        
        # Bulk insert
        if events_to_create:
            try:
                TelemetryEvent.objects.bulk_create(
                    events_to_create,
                    ignore_conflicts=True,  # IntegrityError'ları yoksay
                )
                accepted = len(events_to_create)
            except Exception as e:
                logger.error(f"Bulk insert failed: {e}")
                # Fallback: Tek tek dene
                for event in events_to_create:
                    try:
                        event.save()
                        accepted += 1
                    except IntegrityError:
                        deduped += 1
                    except Exception as save_error:
                        rejected += 1
                        errors.append({
                            'client_event_id': event.client_event_id,
                            'error': str(save_error),
                        })
        
        logger.info(
            f"Event batch processed: session={session.id}, "
            f"accepted={accepted}, deduped={deduped}, rejected={rejected}"
        )
        
        return accepted, deduped, rejected, errors
    
    @classmethod
    def validate_event(cls, event_data: Dict, session: PlaybackSession) -> bool:
        """
        Event'i doğrula.
        
        Kurallar:
        - event_type geçerli olmalı
        - video_ts içerik süresini aşmamalı
        - client_ts makul bir aralıkta olmalı
        """
        # Event type kontrolü
        valid_types = [choice[0] for choice in TelemetryEvent.EventType.choices]
        if event_data.get('event_type') not in valid_types:
            return False
        
        # Video timestamp kontrolü
        video_ts = event_data.get('video_ts')
        if video_ts is not None:
            content_duration = (session.content.duration_minutes or 0) * 60
            if content_duration > 0 and video_ts > content_duration * 1.1:  # %10 tolerans
                return False
        
        # Client timestamp kontrolü (son 24 saat içinde olmalı)
        client_ts = event_data.get('client_ts')
        if client_ts:
            now = timezone.now()
            if client_ts > now or (now - client_ts).total_seconds() > 86400:
                return False
        
        return True
    
    @classmethod
    def get_session_events(
        cls,
        session: PlaybackSession,
        event_types: List[str] = None,
        limit: int = 100,
    ) -> List[TelemetryEvent]:
        """Session'ın event'lerini getir."""
        queryset = TelemetryEvent.objects.filter(session=session)
        
        if event_types:
            queryset = queryset.filter(event_type__in=event_types)
        
        return list(queryset.order_by('-server_ts')[:limit])

