"""
PDF Service
===========

WeasyPrint ile sertifika PDF oluşturma servisi.
"""

import io
import logging
from datetime import date

from django.template import Template, Context
from django.utils import timezone

logger = logging.getLogger(__name__)


# Varsayılan HTML şablonu
DEFAULT_CERTIFICATE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4 landscape;
            margin: 0;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Georgia', 'Times New Roman', serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .certificate {
            width: 1000px;
            height: 700px;
            background: white;
            border: 15px solid #1a1a2e;
            position: relative;
            padding: 40px 60px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .certificate::before {
            content: '';
            position: absolute;
            top: 10px;
            left: 10px;
            right: 10px;
            bottom: 10px;
            border: 2px solid #c9a227;
            pointer-events: none;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo {
            max-height: 60px;
            margin-bottom: 15px;
        }
        
        .institution-name {
            font-size: 16px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        
        .title-section {
            text-align: center;
            margin-bottom: 25px;
        }
        
        .title {
            font-size: 42px;
            color: #1a1a2e;
            font-weight: normal;
            text-transform: uppercase;
            letter-spacing: 8px;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 14px;
            color: #888;
            letter-spacing: 2px;
        }
        
        .content {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .presented-to {
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }
        
        .recipient-name {
            font-size: 36px;
            color: #1a1a2e;
            font-style: italic;
            margin-bottom: 20px;
            border-bottom: 2px solid #c9a227;
            display: inline-block;
            padding-bottom: 5px;
        }
        
        .description {
            font-size: 14px;
            color: #555;
            line-height: 1.8;
            max-width: 700px;
            margin: 0 auto;
        }
        
        .course-title {
            font-weight: bold;
            color: #1a1a2e;
        }
        
        .details {
            display: flex;
            justify-content: center;
            gap: 50px;
            margin-bottom: 30px;
        }
        
        .detail-item {
            text-align: center;
        }
        
        .detail-value {
            font-size: 22px;
            color: #1a1a2e;
            font-weight: bold;
        }
        
        .detail-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            position: absolute;
            bottom: 50px;
            left: 60px;
            right: 60px;
        }
        
        .signature {
            text-align: center;
        }
        
        .signature-line {
            width: 180px;
            border-top: 1px solid #333;
            margin-bottom: 5px;
        }
        
        .signature-name {
            font-size: 12px;
            color: #333;
        }
        
        .signature-title {
            font-size: 10px;
            color: #666;
        }
        
        .qr-section {
            text-align: center;
        }
        
        .qr-code {
            width: 80px;
            height: 80px;
            margin-bottom: 5px;
        }
        
        .verification-code {
            font-size: 9px;
            color: #888;
            letter-spacing: 1px;
        }
        
        .date-section {
            text-align: center;
        }
        
        .date-value {
            font-size: 14px;
            color: #1a1a2e;
        }
        
        .date-label {
            font-size: 10px;
            color: #888;
        }
        
        .skills {
            margin-top: 20px;
            text-align: center;
        }
        
        .skills-title {
            font-size: 11px;
            color: #666;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .skill-tags {
            display: flex;
            justify-content: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .skill-tag {
            background: #f0f0f0;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 10px;
            color: #555;
        }
    </style>
</head>
<body>
    <div class="certificate">
        <div class="header">
            {% if logo_url %}
            <img src="{{ logo_url }}" alt="Logo" class="logo">
            {% endif %}
            <div class="institution-name">{{ institution_name }}</div>
        </div>
        
        <div class="title-section">
            <h1 class="title">Sertifika</h1>
            <div class="subtitle">Başarı Belgesi</div>
        </div>
        
        <div class="content">
            <div class="presented-to">Bu belge</div>
            <div class="recipient-name">{{ recipient_name }}</div>
            <div class="description">
                adına düzenlenmiştir. Adı geçen kişi 
                <span class="course-title">"{{ course_title }}"</span> 
                eğitimini başarıyla tamamlamıştır.
            </div>
        </div>
        
        <div class="details">
            <div class="detail-item">
                <div class="detail-value">{{ completion_percent }}%</div>
                <div class="detail-label">Tamamlama</div>
            </div>
            {% if final_score %}
            <div class="detail-item">
                <div class="detail-value">{{ final_score }}</div>
                <div class="detail-label">Final Notu</div>
            </div>
            {% endif %}
            <div class="detail-item">
                <div class="detail-value">{{ total_hours }} saat</div>
                <div class="detail-label">Eğitim Süresi</div>
            </div>
        </div>
        
        {% if skills %}
        <div class="skills">
            <div class="skills-title">Kazanılan Beceriler</div>
            <div class="skill-tags">
                {% for skill in skills %}
                <span class="skill-tag">{{ skill }}</span>
                {% endfor %}
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            <div class="signature">
                <div class="signature-line"></div>
                <div class="signature-name">{{ issued_by_name }}</div>
                <div class="signature-title">Eğitim Koordinatörü</div>
            </div>
            
            <div class="qr-section">
                <img src="{{ qr_code_url }}" alt="QR Code" class="qr-code">
                <div class="verification-code">{{ verification_code }}</div>
            </div>
            
            <div class="date-section">
                <div class="date-value">{{ completion_date }}</div>
                <div class="date-label">Düzenleme Tarihi</div>
            </div>
        </div>
    </div>
</body>
</html>
"""


class PDFService:
    """
    PDF oluşturma servisi.
    
    WeasyPrint kullanarak HTML'den PDF oluşturur.
    """
    
    @classmethod
    def generate_certificate_pdf(cls, certificate) -> bytes:
        """
        Sertifika PDF'i oluşturur.
        
        Args:
            certificate: Certificate model instance
            
        Returns:
            bytes: PDF içeriği
        """
        from .qr_service import QRService
        
        # QR kod oluştur
        qr_code_url = QRService.generate_qr_data_url(certificate.verify_url)
        
        # Şablon al
        if certificate.template and certificate.template.html_template:
            html_template = certificate.template.html_template
        else:
            html_template = DEFAULT_CERTIFICATE_TEMPLATE
        
        # Context hazırla
        context = {
            'institution_name': certificate.tenant.name if certificate.tenant else 'Akademi',
            'logo_url': cls._get_logo_url(certificate),
            'recipient_name': certificate.user.full_name,
            'course_title': certificate.course.title,
            'completion_percent': certificate.completion_percent,
            'final_score': round(certificate.final_score, 1) if certificate.final_score else None,
            'total_hours': certificate.total_hours,
            'skills': certificate.skills[:5] if certificate.skills else [],  # Max 5 skill
            'completion_date': certificate.completion_date.strftime('%d %B %Y'),
            'verification_code': certificate.verification_code,
            'qr_code_url': qr_code_url,
            'issued_by_name': certificate.issued_by.full_name if certificate.issued_by else 'Yönetim',
        }
        
        # HTML render et
        template = Template(html_template)
        html_content = template.render(Context(context))
        
        # PDF oluştur
        pdf_bytes = cls._html_to_pdf(html_content)
        
        return pdf_bytes
    
    @classmethod
    def _html_to_pdf(cls, html_content: str) -> bytes:
        """HTML'den PDF oluşturur."""
        try:
            from weasyprint import HTML, CSS
            
            # PDF oluştur
            pdf_buffer = io.BytesIO()
            HTML(string=html_content).write_pdf(pdf_buffer)
            
            return pdf_buffer.getvalue()
            
        except ImportError:
            logger.warning("WeasyPrint yüklü değil, basit PDF oluşturuluyor")
            return cls._fallback_pdf(html_content)
    
    @classmethod
    def _fallback_pdf(cls, html_content: str) -> bytes:
        """
        WeasyPrint yoksa basit bir PDF oluşturur.
        
        ReportLab kullanarak temel bir sertifika oluşturur.
        """
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfgen import canvas
            from reportlab.lib.colors import HexColor
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=landscape(A4))
            width, height = landscape(A4)
            
            # Basit sertifika çerçevesi
            c.setStrokeColor(HexColor('#1a1a2e'))
            c.setLineWidth(10)
            c.rect(30, 30, width - 60, height - 60)
            
            # Başlık
            c.setFont("Helvetica-Bold", 36)
            c.setFillColor(HexColor('#1a1a2e'))
            c.drawCentredString(width / 2, height - 120, "SERTİFİKA")
            
            # Alt başlık
            c.setFont("Helvetica", 14)
            c.setFillColor(HexColor('#666666'))
            c.drawCentredString(width / 2, height - 150, "Başarı Belgesi")
            
            # "Bu belge" metni
            c.setFont("Helvetica", 12)
            c.drawCentredString(width / 2, height - 200, "Bu belge aşağıdaki kişiye verilmiştir:")
            
            # Basit metin
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, height - 250, "[Sertifika Bilgileri]")
            
            c.setFont("Helvetica", 10)
            c.drawCentredString(width / 2, 80, "WeasyPrint yükleyerek daha güzel sertifikalar oluşturabilirsiniz.")
            
            c.save()
            return buffer.getvalue()
            
        except ImportError:
            # ReportLab da yoksa boş PDF
            logger.error("PDF oluşturma için kütüphane bulunamadı")
            return b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\ntrailer<</Size 3/Root 1 0 R>>\nstartxref\n95\n%%EOF'
    
    @classmethod
    def _get_logo_url(cls, certificate) -> str:
        """Kurum logosunu döndürür."""
        if certificate.template and certificate.template.logo:
            return certificate.template.logo.url
        return ''

