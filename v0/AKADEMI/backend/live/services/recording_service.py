"""
Recording Service
=================

Kayıt yönetimi servisi.
"""

import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from ..models import (
    LiveSession,
    LiveSessionRecording,
    LiveSessionPolicy,
)

logger = logging.getLogger(__name__)


class RecordingService:
    """
    Kayıt yönetimi servisi.
    """
    
    @classmethod
    @transaction.atomic
    def create_recording(
        cls,
        session: LiveSession,
        provider_recording_id: str,
        provider_url: str = '',
        duration_seconds: int = 0,
        file_size_bytes: int = 0,
        format: str = 'mp4'
    ) -> LiveSessionRecording:
        """
        Yeni kayıt oluştur.
        
        Args:
            session: İlişkili oturum
            provider_recording_id: Provider tarafından verilen ID
            provider_url: Provider'daki kayıt URL'i
            duration_seconds: Süre
            file_size_bytes: Boyut
            format: Format
            
        Returns:
            LiveSessionRecording: Oluşturulan kayıt
        """
        recording = LiveSessionRecording.objects.create(
            session=session,
            tenant=session.tenant,
            provider_recording_id=provider_recording_id,
            provider_url=provider_url,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size_bytes,
            format=format,
            status=LiveSessionRecording.Status.PROCESSING,
            title=f"{session.title} - Kayıt",
        )
        
        # Retention hesapla
        policy = LiveSessionPolicy.get_effective_policy(session)
        if policy and policy.recording_retention_days:
            recording.expires_at = timezone.now() + timedelta(days=policy.recording_retention_days)
            recording.save(update_fields=['expires_at'])
        
        logger.info(f"Recording created: {recording.id} for session {session.id}")
        
        return recording
    
    @classmethod
    @transaction.atomic
    def process_recording(cls, recording: LiveSessionRecording, storage_url: str, storage_path: str) -> None:
        """
        Kayıt işleme tamamlandı.
        
        Provider'dan indirilen ve storage'a yüklenen kayıt.
        
        Args:
            recording: Kayıt
            storage_url: Storage URL
            storage_path: Storage path
        """
        recording.storage_url = storage_url
        recording.storage_path = storage_path
        recording.status = LiveSessionRecording.Status.READY
        recording.save(update_fields=['storage_url', 'storage_path', 'status', 'updated_at'])
        
        logger.info(f"Recording processed: {recording.id}")
    
    @classmethod
    @transaction.atomic
    def publish_recording(cls, recording: LiveSessionRecording, is_public: bool = False) -> None:
        """
        Kaydı yayınla.
        
        Args:
            recording: Kayıt
            is_public: Herkese açık mı
        """
        if recording.status != LiveSessionRecording.Status.READY:
            raise ValueError(f"Cannot publish recording in status: {recording.status}")
        
        recording.status = LiveSessionRecording.Status.PUBLISHED
        recording.is_public = is_public
        recording.published_at = timezone.now()
        recording.save(update_fields=['status', 'is_public', 'published_at', 'updated_at'])
        
        logger.info(f"Recording published: {recording.id}")
    
    @classmethod
    @transaction.atomic
    def unpublish_recording(cls, recording: LiveSessionRecording) -> None:
        """
        Yayından kaldır.
        
        Args:
            recording: Kayıt
        """
        if recording.status != LiveSessionRecording.Status.PUBLISHED:
            raise ValueError(f"Cannot unpublish recording in status: {recording.status}")
        
        recording.status = LiveSessionRecording.Status.READY
        recording.published_at = None
        recording.save(update_fields=['status', 'published_at', 'updated_at'])
        
        logger.info(f"Recording unpublished: {recording.id}")
    
    @classmethod
    def get_access_url(cls, recording: LiveSessionRecording, user=None, expiry_seconds: int = 3600) -> str:
        """
        Erişim URL'i oluştur.
        
        Args:
            recording: Kayıt
            user: Erişen kullanıcı (log için)
            expiry_seconds: URL geçerlilik süresi
            
        Returns:
            str: İmzalı erişim URL'i
        """
        # View count artır
        recording.view_count += 1
        recording.save(update_fields=['view_count'])
        
        if recording.file:
            from backend.storage.services.storage_service import StorageService
            return StorageService.get_file_url(recording.file, expiry_seconds)
        
        return recording.storage_url or recording.provider_url
    
    @classmethod
    def cleanup_expired_recordings(cls) -> int:
        """
        Süresi dolan kayıtları temizle.
        
        Returns:
            int: Silinen kayıt sayısı
        """
        now = timezone.now()
        expired = LiveSessionRecording.objects.filter(
            expires_at__lt=now,
            status__in=[
                LiveSessionRecording.Status.READY,
                LiveSessionRecording.Status.PUBLISHED
            ]
        )
        
        count = 0
        for recording in expired:
            try:
                # Storage'dan sil
                if recording.file:
                    recording.file.delete()
                
                # Status güncelle
                recording.status = LiveSessionRecording.Status.DELETED
                recording.save(update_fields=['status'])
                count += 1
                
                logger.info(f"Recording expired and deleted: {recording.id}")
            except Exception as e:
                logger.error(f"Failed to delete expired recording {recording.id}: {e}")
        
        return count
    
    @classmethod
    def generate_thumbnail(cls, recording: LiveSessionRecording) -> Optional[str]:
        """
        Thumbnail oluştur (FFmpeg ile).
        
        Args:
            recording: Kayıt
            
        Returns:
            str: Thumbnail URL veya None
        """
        # Bu metod FFmpeg subprocess veya external service ile implement edilebilir
        # Placeholder implementasyon
        logger.info(f"Thumbnail generation not implemented for: {recording.id}")
        return None

