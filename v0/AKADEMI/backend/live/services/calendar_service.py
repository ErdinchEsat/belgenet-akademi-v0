"""
Calendar Service
================

Takvim entegrasyonu servisi.
ICS dosyası oluşturma.
"""

import uuid
from datetime import datetime
from typing import Optional

from ..models import LiveSession


class CalendarService:
    """
    Takvim servisi.
    """
    
    @classmethod
    def generate_ics(cls, session: LiveSession) -> str:
        """
        ICS takvim dosyası oluştur.
        
        Args:
            session: Canlı ders oturumu
            
        Returns:
            str: ICS dosya içeriği
        """
        # UID oluştur
        uid = f"{session.id}@edutech.live"
        
        # Tarih formatı (UTC)
        start = cls._format_datetime(session.scheduled_start)
        end = cls._format_datetime(session.scheduled_end)
        now = cls._format_datetime(datetime.utcnow())
        
        # Organizatör
        organizer_name = session.created_by.full_name if session.created_by else "EduTech"
        organizer_email = session.created_by.email if session.created_by else "noreply@edutech.com"
        
        # Açıklama
        description = session.description or ''
        if session.room_url:
            description += f"\\n\\nKatılım Linki: {session.room_url}"
        
        # ICS içeriği
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//EduTech//Live Session//TR",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now}",
            f"DTSTART:{start}",
            f"DTEND:{end}",
            f"SUMMARY:{cls._escape_text(session.title)}",
            f"DESCRIPTION:{cls._escape_text(description)}",
            f"LOCATION:{session.room_url or 'Online'}",
            f"ORGANIZER;CN={organizer_name}:mailto:{organizer_email}",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
        ]
        
        # Hatırlatıcılar
        # 1 saat önce
        ics_lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT1H",
            "ACTION:DISPLAY",
            "DESCRIPTION:Canlı ders 1 saat sonra başlayacak",
            "END:VALARM",
        ])
        
        # 10 dakika önce
        ics_lines.extend([
            "BEGIN:VALARM",
            "TRIGGER:-PT10M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Canlı ders 10 dakika sonra başlayacak",
            "END:VALARM",
        ])
        
        ics_lines.extend([
            "END:VEVENT",
            "END:VCALENDAR",
        ])
        
        return "\r\n".join(ics_lines)
    
    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        """Datetime'ı ICS formatına çevir."""
        if dt.tzinfo:
            # UTC'ye çevir
            from django.utils import timezone
            dt = timezone.localtime(dt, timezone.utc)
        return dt.strftime("%Y%m%dT%H%M%SZ")
    
    @staticmethod
    def _escape_text(text: str) -> str:
        """ICS için text escape."""
        if not text:
            return ""
        
        # Özel karakterleri escape et
        text = text.replace("\\", "\\\\")
        text = text.replace(";", "\\;")
        text = text.replace(",", "\\,")
        text = text.replace("\n", "\\n")
        text = text.replace("\r", "")
        
        return text
    
    @classmethod
    def generate_google_calendar_url(cls, session: LiveSession) -> str:
        """
        Google Calendar URL oluştur.
        
        Args:
            session: Canlı ders oturumu
            
        Returns:
            str: Google Calendar URL
        """
        from urllib.parse import urlencode
        
        start = session.scheduled_start.strftime("%Y%m%dT%H%M%SZ")
        end = session.scheduled_end.strftime("%Y%m%dT%H%M%SZ")
        
        details = session.description or ''
        if session.room_url:
            details += f"\n\nKatılım Linki: {session.room_url}"
        
        params = {
            'action': 'TEMPLATE',
            'text': session.title,
            'dates': f"{start}/{end}",
            'details': details,
            'location': session.room_url or 'Online',
            'sf': 'true',
        }
        
        return f"https://calendar.google.com/calendar/render?{urlencode(params)}"
    
    @classmethod
    def generate_outlook_url(cls, session: LiveSession) -> str:
        """
        Outlook Calendar URL oluştur.
        
        Args:
            session: Canlı ders oturumu
            
        Returns:
            str: Outlook Calendar URL
        """
        from urllib.parse import urlencode, quote
        
        start = session.scheduled_start.strftime("%Y-%m-%dT%H:%M:%S")
        end = session.scheduled_end.strftime("%Y-%m-%dT%H:%M:%S")
        
        body = session.description or ''
        if session.room_url:
            body += f"\n\nKatılım Linki: {session.room_url}"
        
        params = {
            'path': '/calendar/action/compose',
            'rru': 'addevent',
            'subject': session.title,
            'startdt': start,
            'enddt': end,
            'body': body,
            'location': session.room_url or 'Online',
        }
        
        return f"https://outlook.live.com/calendar/0/deeplink/compose?{urlencode(params)}"

