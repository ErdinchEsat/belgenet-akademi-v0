"""
Image Service
=============

Görsel işleme servisi.
Resize, crop, format dönüşümü.
"""

import io
import logging
from typing import Tuple, Optional

from django.core.files.base import ContentFile

from ..models import FileUpload, ImageVariant

logger = logging.getLogger(__name__)


# Varyant boyutları
VARIANT_SIZES = {
    'thumbnail': (150, 150),
    'small': (300, 300),
    'medium': (600, 600),
    'large': (1200, 1200),
}


class ImageService:
    """
    Görsel işleme servisi.
    """
    
    @classmethod
    def create_variants(
        cls,
        file_upload: FileUpload,
        sizes: list = None,
    ) -> list:
        """
        Görsel varyantları oluşturur.
        
        Args:
            file_upload: Orijinal görsel
            sizes: Oluşturulacak boyutlar (None ise tümü)
            
        Returns:
            list: Oluşturulan ImageVariant listesi
        """
        if not file_upload.is_image:
            raise ValueError("Dosya bir görsel değil")
        
        try:
            from PIL import Image
        except ImportError:
            logger.warning("Pillow yüklü değil, varyantlar oluşturulamadı")
            return []
        
        sizes = sizes or list(VARIANT_SIZES.keys())
        variants = []
        
        try:
            # Orijinal görseli aç
            file_upload.file.seek(0)
            original = Image.open(file_upload.file)
            
            # RGBA -> RGB dönüşümü (JPEG için)
            if original.mode in ('RGBA', 'P'):
                background = Image.new('RGB', original.size, (255, 255, 255))
                if original.mode == 'P':
                    original = original.convert('RGBA')
                background.paste(original, mask=original.split()[-1])
                original = background
            elif original.mode != 'RGB':
                original = original.convert('RGB')
            
            for size_name in sizes:
                if size_name not in VARIANT_SIZES:
                    continue
                
                max_size = VARIANT_SIZES[size_name]
                variant = cls._create_single_variant(
                    file_upload,
                    original,
                    size_name,
                    max_size,
                )
                if variant:
                    variants.append(variant)
            
            logger.info(f"Görsel varyantları oluşturuldu: {file_upload.id} - {len(variants)} adet")
            
        except Exception as e:
            logger.error(f"Varyant oluşturma hatası: {e}")
        
        return variants
    
    @classmethod
    def _create_single_variant(
        cls,
        file_upload: FileUpload,
        original,  # PIL Image
        size_name: str,
        max_size: Tuple[int, int],
    ) -> Optional[ImageVariant]:
        """
        Tek bir varyant oluşturur.
        """
        from PIL import Image
        
        try:
            # Kopyala ve resize et
            img = original.copy()
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Dosyaya kaydet
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            # Varyant kaydı oluştur
            variant_filename = f"{file_upload.id}_{size_name}.jpg"
            
            variant = ImageVariant(
                original=file_upload,
                size=size_name,
                width=img.width,
                height=img.height,
                file_size=buffer.getbuffer().nbytes,
            )
            variant.file.save(variant_filename, ContentFile(buffer.read()), save=True)
            
            return variant
            
        except Exception as e:
            logger.error(f"Varyant oluşturma hatası ({size_name}): {e}")
            return None
    
    @classmethod
    def get_variant_url(
        cls,
        file_upload: FileUpload,
        size: str = 'medium',
    ) -> str:
        """
        Belirli boyuttaki varyant URL'ini döndürür.
        
        Args:
            file_upload: Görsel dosyası
            size: Varyant boyutu
            
        Returns:
            str: Varyant URL'i (yoksa orijinal)
        """
        if not file_upload.is_image:
            return file_upload.file_url
        
        variant = file_upload.variants.filter(size=size).first()
        if variant:
            return variant.url
        
        # Varyant yoksa orijinali döndür
        return file_upload.file_url
    
    @classmethod
    def crop_image(
        cls,
        file_upload: FileUpload,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> FileUpload:
        """
        Görseli kırpar.
        
        Args:
            file_upload: Görsel dosyası
            x, y: Başlangıç koordinatları
            width, height: Kırpılacak alan boyutları
            
        Returns:
            FileUpload: Yeni kırpılmış görsel
        """
        from PIL import Image
        
        file_upload.file.seek(0)
        img = Image.open(file_upload.file)
        
        # Kırp
        cropped = img.crop((x, y, x + width, y + height))
        
        # Kaydet
        buffer = io.BytesIO()
        format_map = {
            'image/jpeg': 'JPEG',
            'image/png': 'PNG',
            'image/gif': 'GIF',
            'image/webp': 'WEBP',
        }
        save_format = format_map.get(file_upload.mime_type, 'JPEG')
        
        if save_format == 'JPEG' and cropped.mode in ('RGBA', 'P'):
            cropped = cropped.convert('RGB')
        
        cropped.save(buffer, format=save_format, quality=90)
        buffer.seek(0)
        
        # Yeni dosya olarak kaydet
        from .storage_service import StorageService
        
        new_filename = f"cropped_{file_upload.original_filename}"
        new_file = ContentFile(buffer.read(), name=new_filename)
        
        return StorageService.upload_file(
            file=new_file,
            category=file_upload.category,
            user=file_upload.uploaded_by,
            tenant=file_upload.tenant,
            metadata={'cropped_from': str(file_upload.id)},
        )
    
    @classmethod
    def optimize_image(
        cls,
        file_upload: FileUpload,
        quality: int = 85,
        max_dimension: int = 2048,
    ) -> None:
        """
        Görseli optimize eder (boyut ve kalite).
        
        Args:
            file_upload: Görsel dosyası
            quality: JPEG kalitesi (1-100)
            max_dimension: Maksimum boyut
        """
        from PIL import Image
        
        file_upload.file.seek(0)
        img = Image.open(file_upload.file)
        
        # Boyut kontrolü
        if max(img.size) > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
        
        # RGB'ye dönüştür
        if img.mode in ('RGBA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Optimize et ve kaydet
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        
        # Mevcut dosyayı güncelle
        file_upload.file.delete(save=False)
        file_upload.file.save(
            file_upload.original_filename,
            ContentFile(buffer.read()),
            save=False,
        )
        file_upload.file_size = buffer.getbuffer().nbytes
        file_upload.width = img.width
        file_upload.height = img.height
        file_upload.save()
        
        logger.info(f"Görsel optimize edildi: {file_upload.id}")

