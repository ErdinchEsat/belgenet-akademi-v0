"""
QR Code Service
===============

QR kod oluşturma servisi.
"""

import io
import base64
import logging

logger = logging.getLogger(__name__)


class QRService:
    """
    QR kod servisi.
    
    Sertifika doğrulama için QR kod oluşturur.
    """
    
    @classmethod
    def generate_qr_code(cls, data: str, size: int = 200) -> bytes:
        """
        QR kod görseli oluşturur.
        
        Args:
            data: QR koda kodlanacak veri (URL)
            size: Görsel boyutu (piksel)
            
        Returns:
            bytes: PNG görsel verisi
        """
        try:
            import qrcode
            from qrcode.image.pil import PilImage
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Görsel oluştur
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Boyutlandır
            img = img.resize((size, size))
            
            # Bytes'a çevir
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            
            return buffer.getvalue()
            
        except ImportError:
            logger.warning("qrcode kütüphanesi yüklü değil")
            return cls._generate_placeholder_qr(size)
    
    @classmethod
    def generate_qr_data_url(cls, data: str, size: int = 200) -> str:
        """
        QR kod için data URL oluşturur.
        
        HTML img src'de kullanılabilir.
        
        Args:
            data: QR koda kodlanacak veri
            size: Görsel boyutu
            
        Returns:
            str: data:image/png;base64,... formatında URL
        """
        qr_bytes = cls.generate_qr_code(data, size)
        b64_data = base64.b64encode(qr_bytes).decode('utf-8')
        return f"data:image/png;base64,{b64_data}"
    
    @classmethod
    def _generate_placeholder_qr(cls, size: int) -> bytes:
        """
        QR kod placeholder'ı oluşturur.
        
        qrcode kütüphanesi yoksa basit bir görsel döndürür.
        """
        try:
            from PIL import Image, ImageDraw
            
            img = Image.new('RGB', (size, size), 'white')
            draw = ImageDraw.Draw(img)
            
            # Basit kare çiz
            margin = size // 10
            draw.rectangle(
                [margin, margin, size - margin, size - margin],
                outline='black',
                width=2
            )
            
            # "QR" yaz
            draw.text((size // 3, size // 3), "QR", fill='black')
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except ImportError:
            # Pillow da yoksa 1x1 beyaz piksel
            return (
                b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
                b'\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00'
                b'\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02'
                b'\xfe\xa7V\xbd\x00\x00\x00\x00IEND\xaeB`\x82'
            )
    
    @classmethod
    def verify_qr_data(cls, qr_data: str) -> dict:
        """
        QR kod verisini doğrular.
        
        Args:
            qr_data: QR koddan okunan veri
            
        Returns:
            dict: Doğrulama sonucu
        """
        # URL'den doğrulama kodunu çıkar
        # Format: .../certificates/verify/CERT-XXXXXXXX
        
        if '/verify/' not in qr_data:
            return {'valid': False, 'error': 'Geçersiz QR kod formatı'}
        
        try:
            verification_code = qr_data.split('/verify/')[-1].strip('/')
            
            if not verification_code.startswith('CERT-'):
                return {'valid': False, 'error': 'Geçersiz doğrulama kodu'}
            
            return {
                'valid': True,
                'verification_code': verification_code,
            }
            
        except Exception as e:
            return {'valid': False, 'error': str(e)}

