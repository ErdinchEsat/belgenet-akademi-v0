"""
Storage Service
===============

Dosya yükleme ve yönetim servisi.
"""

import hashlib
import logging
import os
from datetime import timedelta
from typing import Optional, BinaryIO
from uuid import UUID

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.utils import timezone

from ..models import FileUpload, UploadSession
from ..validators import validate_file

logger = logging.getLogger(__name__)


class StorageService:
    """
    Dosya depolama servisi.
    
    Dosya yükleme, silme, URL oluşturma işlemlerini yönetir.
    """
    
    CHUNK_SESSION_EXPIRY_HOURS = 24
    
    @classmethod
    def upload_file(
        cls,
        file: BinaryIO,
        category: str,
        user,
        tenant,
        content_type: str = '',
        object_id: str = '',
        is_public: bool = False,
        metadata: dict = None,
    ) -> FileUpload:
        """
        Dosya yükler.
        
        Args:
            file: Yüklenecek dosya
            category: Dosya kategorisi
            user: Yükleyen kullanıcı
            tenant: Tenant
            content_type: İlişkili model tipi
            object_id: İlişkili nesne ID
            is_public: Herkese açık mı
            metadata: Ek veriler
            
        Returns:
            FileUpload: Oluşturulan dosya kaydı
        """
        # Validasyon
        validation_result = validate_file(file, category)
        
        # Dosya hash'i hesapla
        file_hash = cls._calculate_hash(file)
        
        # Dosya boyutu
        file.seek(0, 2)  # Sona git
        file_size = file.tell()
        file.seek(0)  # Başa dön
        
        # Dosya kaydı oluştur
        file_upload = FileUpload(
            original_filename=file.name,
            category=category,
            mime_type=validation_result['mime_type'],
            file_size=file_size,
            file_hash=file_hash,
            width=validation_result.get('width'),
            height=validation_result.get('height'),
            uploaded_by=user,
            tenant=tenant,
            content_type=content_type,
            object_id=object_id,
            is_public=is_public,
            metadata=metadata or {},
            status=FileUpload.Status.PROCESSING,
        )
        
        try:
            # Dosyayı kaydet
            file_upload.file.save(file.name, file, save=False)
            file_upload.status = FileUpload.Status.COMPLETED
            file_upload.save()
            
            logger.info(
                f"Dosya yüklendi: {file_upload.id} - {file_upload.original_filename}"
            )
            
        except Exception as e:
            file_upload.status = FileUpload.Status.FAILED
            file_upload.error_message = str(e)
            file_upload.save()
            logger.error(f"Dosya yükleme hatası: {e}")
            raise
        
        return file_upload
    
    @classmethod
    def delete_file(cls, file_upload: FileUpload, hard_delete: bool = False):
        """
        Dosyayı siler.
        
        Args:
            file_upload: Silinecek dosya
            hard_delete: Fiziksel olarak sil
        """
        if hard_delete:
            # Fiziksel silme
            if file_upload.file:
                file_upload.file.delete(save=False)
            
            # Varyantları sil
            for variant in file_upload.variants.all():
                if variant.file:
                    variant.file.delete(save=False)
                variant.delete()
            
            file_upload.delete()
            logger.info(f"Dosya kalıcı olarak silindi: {file_upload.id}")
        else:
            # Soft delete
            file_upload.mark_deleted()
            logger.info(f"Dosya silinmiş olarak işaretlendi: {file_upload.id}")
    
    @classmethod
    def get_file_url(
        cls,
        file_upload: FileUpload,
        expiry_seconds: int = 3600,
    ) -> str:
        """
        Dosya URL'i döndürür.
        
        S3/MinIO için imzalı URL oluşturur.
        
        Args:
            file_upload: Dosya
            expiry_seconds: URL geçerlilik süresi
            
        Returns:
            str: Dosya URL'i
        """
        if not file_upload.file:
            return ''
        
        # Public dosyalar için doğrudan URL
        if file_upload.is_public:
            return file_upload.file.url
        
        # S3/MinIO için imzalı URL
        storage = default_storage
        if hasattr(storage, 'url') and hasattr(storage, 'bucket'):
            try:
                return storage.url(
                    file_upload.file.name,
                    parameters={'ResponseContentDisposition': f'inline; filename="{file_upload.original_filename}"'},
                    expire=expiry_seconds,
                )
            except Exception:
                pass
        
        return file_upload.file.url
    
    @classmethod
    def get_download_url(
        cls,
        file_upload: FileUpload,
        expiry_seconds: int = 3600,
    ) -> str:
        """
        İndirme URL'i döndürür.
        
        Content-Disposition: attachment header'ı ile.
        """
        if not file_upload.file:
            return ''
        
        storage = default_storage
        if hasattr(storage, 'url') and hasattr(storage, 'bucket'):
            try:
                return storage.url(
                    file_upload.file.name,
                    parameters={'ResponseContentDisposition': f'attachment; filename="{file_upload.original_filename}"'},
                    expire=expiry_seconds,
                )
            except Exception:
                pass
        
        return file_upload.file.url
    
    @classmethod
    def duplicate_check(cls, file_hash: str, tenant) -> Optional[FileUpload]:
        """
        Aynı dosyanın daha önce yüklenip yüklenmediğini kontrol eder.
        
        Args:
            file_hash: Dosya hash'i
            tenant: Tenant
            
        Returns:
            FileUpload or None: Mevcut dosya varsa döndürür
        """
        return FileUpload.objects.filter(
            file_hash=file_hash,
            tenant=tenant,
            status=FileUpload.Status.COMPLETED,
        ).first()
    
    # =========================================================================
    # CHUNK UPLOAD (Büyük dosyalar için)
    # =========================================================================
    
    @classmethod
    def create_upload_session(
        cls,
        filename: str,
        file_size: int,
        category: str,
        user,
        tenant,
        chunk_size: int = 5 * 1024 * 1024,  # 5MB
        metadata: dict = None,
    ) -> UploadSession:
        """
        Büyük dosya yüklemesi için oturum oluşturur.
        
        Args:
            filename: Dosya adı
            file_size: Toplam dosya boyutu
            category: Kategori
            user: Kullanıcı
            tenant: Tenant
            chunk_size: Parça boyutu
            metadata: Ek veriler
            
        Returns:
            UploadSession: Yükleme oturumu
        """
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        session = UploadSession.objects.create(
            filename=filename,
            file_size=file_size,
            chunk_size=chunk_size,
            total_chunks=total_chunks,
            category=category,
            uploaded_by=user,
            tenant=tenant,
            metadata=metadata or {},
            expires_at=timezone.now() + timedelta(hours=cls.CHUNK_SESSION_EXPIRY_HOURS),
        )
        
        logger.info(f"Yükleme oturumu oluşturuldu: {session.id}")
        return session
    
    @classmethod
    def upload_chunk(
        cls,
        session_id: UUID,
        chunk_number: int,
        chunk_data: bytes,
    ) -> UploadSession:
        """
        Dosya parçası yükler.
        
        Args:
            session_id: Oturum ID
            chunk_number: Parça numarası (0-indexed)
            chunk_data: Parça verisi
            
        Returns:
            UploadSession: Güncel oturum
        """
        session = UploadSession.objects.get(id=session_id)
        
        if session.is_expired:
            raise ValueError("Yükleme oturumu süresi dolmuş")
        
        if session.is_completed:
            raise ValueError("Yükleme zaten tamamlanmış")
        
        # Parçayı geçici olarak kaydet
        chunk_path = f"chunks/{session_id}/{chunk_number}"
        default_storage.save(chunk_path, ContentFile(chunk_data))
        
        session.uploaded_chunks += 1
        session.save(update_fields=['uploaded_chunks'])
        
        logger.debug(f"Chunk yüklendi: {session_id} - {chunk_number + 1}/{session.total_chunks}")
        
        return session
    
    @classmethod
    @transaction.atomic
    def complete_upload_session(cls, session_id: UUID) -> FileUpload:
        """
        Yükleme oturumunu tamamlar ve dosyayı birleştirir.
        
        Args:
            session_id: Oturum ID
            
        Returns:
            FileUpload: Oluşturulan dosya
        """
        session = UploadSession.objects.get(id=session_id)
        
        if session.uploaded_chunks != session.total_chunks:
            raise ValueError(
                f"Tüm parçalar yüklenmemiş: {session.uploaded_chunks}/{session.total_chunks}"
            )
        
        # Parçaları birleştir
        combined_data = b''
        for i in range(session.total_chunks):
            chunk_path = f"chunks/{session_id}/{i}"
            chunk_file = default_storage.open(chunk_path, 'rb')
            combined_data += chunk_file.read()
            chunk_file.close()
            # Parçayı sil
            default_storage.delete(chunk_path)
        
        # Dosyayı oluştur
        file_obj = ContentFile(combined_data, name=session.filename)
        
        file_upload = cls.upload_file(
            file=file_obj,
            category=session.category,
            user=session.uploaded_by,
            tenant=session.tenant,
            metadata=session.metadata,
        )
        
        # Oturumu güncelle
        session.is_completed = True
        session.completed_file = file_upload
        session.save()
        
        logger.info(f"Yükleme oturumu tamamlandı: {session_id} -> {file_upload.id}")
        
        return file_upload
    
    # =========================================================================
    # YARDIMCI METODLAR
    # =========================================================================
    
    @staticmethod
    def _calculate_hash(file: BinaryIO) -> str:
        """Dosya SHA-256 hash'i hesaplar."""
        sha256_hash = hashlib.sha256()
        
        file.seek(0)
        for chunk in iter(lambda: file.read(8192), b""):
            sha256_hash.update(chunk)
        file.seek(0)
        
        return sha256_hash.hexdigest()
    
    @classmethod
    def cleanup_expired_sessions(cls):
        """Süresi dolmuş yükleme oturumlarını temizler."""
        expired = UploadSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_completed=False,
        )
        
        for session in expired:
            # Parçaları sil
            for i in range(session.total_chunks):
                chunk_path = f"chunks/{session.id}/{i}"
                try:
                    default_storage.delete(chunk_path)
                except Exception:
                    pass
        
        count = expired.count()
        expired.delete()
        
        if count > 0:
            logger.info(f"{count} süresi dolmuş yükleme oturumu temizlendi")
        
        return count
    
    @classmethod
    def cleanup_deleted_files(cls, days: int = 30):
        """
        Belirli bir süredir silinmiş dosyaları kalıcı olarak siler.
        
        Args:
            days: Gün sayısı
        """
        cutoff = timezone.now() - timedelta(days=days)
        
        deleted_files = FileUpload.objects.filter(
            status=FileUpload.Status.DELETED,
            updated_at__lt=cutoff,
        )
        
        for file_upload in deleted_files:
            cls.delete_file(file_upload, hard_delete=True)
        
        logger.info(f"{deleted_files.count()} silinen dosya kalıcı olarak kaldırıldı")

