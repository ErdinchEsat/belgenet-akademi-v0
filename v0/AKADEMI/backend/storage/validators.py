"""
Storage Validators
==================

Dosya yükleme validasyonları.
- Dosya boyutu kontrolü
- MIME type kontrolü
- Uzantı kontrolü
- Virus tarama (opsiyonel)
"""

import os
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.conf import settings


# =============================================================================
# DOSYA BOYUTU LİMİTLERİ (bytes)
# =============================================================================
FILE_SIZE_LIMITS = {
    'profile': 5 * 1024 * 1024,        # 5 MB
    'assignment': 50 * 1024 * 1024,    # 50 MB
    'submission': 100 * 1024 * 1024,   # 100 MB
    'material': 500 * 1024 * 1024,     # 500 MB
    'certificate': 10 * 1024 * 1024,   # 10 MB
    'document': 50 * 1024 * 1024,      # 50 MB
    'attachment': 25 * 1024 * 1024,    # 25 MB
    'other': 25 * 1024 * 1024,         # 25 MB
    'default': 25 * 1024 * 1024,       # 25 MB
}

# Settings'ten override al
if hasattr(settings, 'FILE_SIZE_LIMITS'):
    FILE_SIZE_LIMITS.update(settings.FILE_SIZE_LIMITS)


# =============================================================================
# İZİN VERİLEN DOSYA TİPLERİ
# =============================================================================
ALLOWED_MIME_TYPES = {
    'profile': [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
    ],
    'assignment': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'application/zip',
        'application/x-rar-compressed',
        'image/jpeg',
        'image/png',
        'image/gif',
    ],
    'submission': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'application/zip',
        'application/x-rar-compressed',
        'application/x-7z-compressed',
        'image/jpeg',
        'image/png',
        'image/gif',
        'video/mp4',
        'video/webm',
        'audio/mpeg',
        'audio/wav',
    ],
    'material': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'text/plain',
        'text/csv',
        'text/html',
        'application/zip',
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/svg+xml',
        'video/mp4',
        'video/webm',
        'audio/mpeg',
        'audio/wav',
    ],
    'certificate': [
        'application/pdf',
        'image/png',
        'image/jpeg',
    ],
    'document': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'text/csv',
    ],
    'attachment': [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
        'image/jpeg',
        'image/png',
        'image/gif',
        'application/zip',
    ],
}

# Settings'ten override al
if hasattr(settings, 'ALLOWED_MIME_TYPES'):
    ALLOWED_MIME_TYPES.update(settings.ALLOWED_MIME_TYPES)


# =============================================================================
# UZANTI HARİTASI
# =============================================================================
EXTENSION_MIME_MAP = {
    # Görseller
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.webp': 'image/webp',
    '.svg': 'image/svg+xml',
    # Dökümanlar
    '.pdf': 'application/pdf',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xls': 'application/vnd.ms-excel',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.ppt': 'application/vnd.ms-powerpoint',
    '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    '.txt': 'text/plain',
    '.csv': 'text/csv',
    '.html': 'text/html',
    # Arşivler
    '.zip': 'application/zip',
    '.rar': 'application/x-rar-compressed',
    '.7z': 'application/x-7z-compressed',
    # Video
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
    '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime',
    # Ses
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
}


# =============================================================================
# YASAKLI UZANTILAR (Güvenlik)
# =============================================================================
BLOCKED_EXTENSIONS = [
    '.exe', '.bat', '.cmd', '.com', '.msi',
    '.sh', '.bash', '.zsh',
    '.js', '.vbs', '.wsf', '.wsh',
    '.ps1', '.psm1', '.psd1',
    '.php', '.php3', '.php4', '.php5', '.phtml',
    '.asp', '.aspx', '.cer', '.csr',
    '.dll', '.sys', '.drv',
    '.scr', '.pif', '.application',
    '.gadget', '.msc', '.msp', '.reg',
    '.jar', '.class',
]


def validate_file_size(file, category='default'):
    """
    Dosya boyutunu kontrol eder.
    
    Args:
        file: Yüklenen dosya
        category: Dosya kategorisi
        
    Raises:
        ValidationError: Boyut sınırı aşılırsa
    """
    max_size = FILE_SIZE_LIMITS.get(category, FILE_SIZE_LIMITS['default'])
    
    if file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file.size / (1024 * 1024)
        raise ValidationError(
            _('Dosya boyutu çok büyük. Maksimum: %(max)s MB, Yüklenen: %(size).2f MB'),
            params={'max': max_mb, 'size': file_mb},
            code='file_too_large',
        )


def validate_extension(filename, category='default'):
    """
    Dosya uzantısını kontrol eder.
    
    Args:
        filename: Dosya adı
        category: Dosya kategorisi
        
    Raises:
        ValidationError: Uzantı yasaklıysa veya izin verilmiyorsa
    """
    ext = os.path.splitext(filename)[1].lower()
    
    # Yasaklı uzantı kontrolü
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(
            _('Bu dosya türü yüklenemez: %(ext)s'),
            params={'ext': ext},
            code='blocked_extension',
        )
    
    # İzin verilen uzantı kontrolü
    allowed_mimes = ALLOWED_MIME_TYPES.get(category, [])
    if allowed_mimes:
        expected_mime = EXTENSION_MIME_MAP.get(ext)
        if expected_mime and expected_mime not in allowed_mimes:
            raise ValidationError(
                _('Bu kategori için bu dosya türü kabul edilmiyor: %(ext)s'),
                params={'ext': ext},
                code='invalid_extension',
            )


def validate_mime_type(file, category='default'):
    """
    MIME tipini kontrol eder.
    
    İçerik bazlı kontrol yapar (magic bytes).
    
    Args:
        file: Yüklenen dosya
        category: Dosya kategorisi
        
    Raises:
        ValidationError: MIME tipi izin verilmiyorsa
    """
    try:
        import magic
        
        # Dosyanın başını oku
        file.seek(0)
        header = file.read(2048)
        file.seek(0)
        
        # MIME tipini tespit et
        mime = magic.from_buffer(header, mime=True)
        
    except ImportError:
        # python-magic yüklü değilse, uzantıdan tahmin et
        ext = os.path.splitext(file.name)[1].lower()
        mime = EXTENSION_MIME_MAP.get(ext, 'application/octet-stream')
    
    # İzin verilen tipleri kontrol et
    allowed_mimes = ALLOWED_MIME_TYPES.get(category, [])
    if allowed_mimes and mime not in allowed_mimes:
        raise ValidationError(
            _('Bu dosya türü bu kategori için kabul edilmiyor: %(mime)s'),
            params={'mime': mime},
            code='invalid_mime_type',
        )
    
    return mime


def validate_image_dimensions(file, max_width=4096, max_height=4096, min_width=10, min_height=10):
    """
    Görsel boyutlarını kontrol eder.
    
    Args:
        file: Görsel dosyası
        max_width, max_height: Maksimum boyutlar
        min_width, min_height: Minimum boyutlar
        
    Raises:
        ValidationError: Boyutlar uygun değilse
    """
    try:
        from PIL import Image
        
        file.seek(0)
        img = Image.open(file)
        width, height = img.size
        file.seek(0)
        
        if width > max_width or height > max_height:
            raise ValidationError(
                _('Görsel boyutu çok büyük. Maksimum: %(max_w)sx%(max_h)s, Yüklenen: %(w)sx%(h)s'),
                params={'max_w': max_width, 'max_h': max_height, 'w': width, 'h': height},
                code='image_too_large',
            )
        
        if width < min_width or height < min_height:
            raise ValidationError(
                _('Görsel boyutu çok küçük. Minimum: %(min_w)sx%(min_h)s'),
                params={'min_w': min_width, 'min_h': min_height},
                code='image_too_small',
            )
        
        return width, height
        
    except ImportError:
        return None, None
    except Exception as e:
        raise ValidationError(
            _('Görsel işlenemedi: %(error)s'),
            params={'error': str(e)},
            code='image_processing_error',
        )


def validate_file(file, category='default', check_dimensions=True):
    """
    Kapsamlı dosya validasyonu.
    
    Args:
        file: Yüklenen dosya
        category: Dosya kategorisi
        check_dimensions: Görsel boyutu kontrol edilsin mi
        
    Returns:
        dict: Dosya bilgileri (mime_type, width, height)
        
    Raises:
        ValidationError: Validasyon başarısızsa
    """
    # Boyut kontrolü
    validate_file_size(file, category)
    
    # Uzantı kontrolü
    validate_extension(file.name, category)
    
    # MIME tipi kontrolü
    mime_type = validate_mime_type(file, category)
    
    result = {
        'mime_type': mime_type,
        'width': None,
        'height': None,
    }
    
    # Görsel boyut kontrolü
    if check_dimensions and mime_type.startswith('image/'):
        width, height = validate_image_dimensions(file)
        result['width'] = width
        result['height'] = height
    
    return result


class FileValidator:
    """
    Dosya validator sınıfı.
    
    Serializer'larda kullanım için.
    """
    
    def __init__(self, category='default', max_size=None, allowed_types=None):
        self.category = category
        self.max_size = max_size
        self.allowed_types = allowed_types
    
    def __call__(self, file):
        # Özel boyut limiti
        if self.max_size:
            if file.size > self.max_size:
                max_mb = self.max_size / (1024 * 1024)
                raise ValidationError(
                    _('Dosya boyutu %(max)s MB\'ı geçemez.'),
                    params={'max': max_mb},
                )
        else:
            validate_file_size(file, self.category)
        
        # Uzantı ve MIME kontrolü
        validate_extension(file.name, self.category)
        validate_mime_type(file, self.category)

