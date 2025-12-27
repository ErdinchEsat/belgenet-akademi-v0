"""
Integrity Service
=================

Bütünlük kontrol iş mantığı.
"""

import logging
import hashlib
from typing import Dict, Optional, List, Tuple
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.player.models import PlaybackSession
from backend.courses.models import CourseContent
from ..models import (
    DeviceFingerprint,
    IntegrityCheck,
    PlaybackAnomaly,
    UserIntegrityScore,
    IntegrityConfig,
)

logger = logging.getLogger(__name__)


class IntegrityService:
    """
    Bütünlük kontrol servisi.
    
    Sorumluluklar:
    - Playback doğrulama
    - Anomali tespiti
    - Cihaz yönetimi
    - Skor hesaplama
    """
    
    # Varsayılan eşik değerleri
    DEFAULT_MIN_VISIBILITY = 0.7
    DEFAULT_MIN_PLAYBACK = 0.6
    DEFAULT_MIN_OVERALL = 0.5
    DEFAULT_MAX_SPEED = 2.0
    DEFAULT_MAX_SEEK_RATIO = 0.5  # Videonun %50'sinden fazla atlama
    
    # ============ Ana Doğrulama ============
    
    @classmethod
    @transaction.atomic
    def verify_playback(
        cls,
        user,
        session: PlaybackSession,
        video_position: int,
        tab_visibility_ratio: float,
        playback_speed: float,
        seek_count: int,
        pause_count: int,
        total_pause_duration: int,
        elapsed_seconds: int,
        device_data: Dict = None,
    ) -> IntegrityCheck:
        """
        Playback bütünlüğünü doğrula.
        """
        # Cihaz kaydı
        device = None
        if device_data:
            device = cls.get_or_create_device(user, device_data)
        
        # Kontrolleri çalıştır
        checks = []
        
        # 1. Tab visibility kontrolü
        visibility_check = cls._check_visibility(tab_visibility_ratio)
        checks.append(visibility_check)
        
        # 2. Playback speed kontrolü
        speed_check = cls._check_playback_speed(playback_speed)
        checks.append(speed_check)
        
        # 3. Seek pattern kontrolü
        content = session.content
        seek_check = cls._check_seek_pattern(
            seek_count, video_position, content.duration_minutes * 60
        )
        checks.append(seek_check)
        
        # 4. Timing consistency kontrolü
        timing_check = cls._check_timing_consistency(
            elapsed_seconds, video_position, playback_speed, total_pause_duration
        )
        checks.append(timing_check)
        
        # Skorları hesapla
        visibility_score = visibility_check['value']
        playback_score = (speed_check['value'] + seek_check['value']) / 2
        timing_score = timing_check['value']
        overall_score = (visibility_score + playback_score + timing_score) / 3
        
        # Durum belirle
        config = cls.get_config(user.tenant)
        if overall_score < config.min_overall_score:
            status = IntegrityCheck.CheckStatus.FAILED
        elif overall_score < 0.8:
            status = IntegrityCheck.CheckStatus.WARNING
        else:
            status = IntegrityCheck.CheckStatus.PASSED
        
        # Kayıt oluştur
        check = IntegrityCheck.objects.create(
            tenant=user.tenant,
            session=session,
            user=user,
            device=device,
            status=status,
            visibility_score=visibility_score,
            playback_score=playback_score,
            timing_score=timing_score,
            overall_score=overall_score,
            checks_performed=checks,
            video_position=video_position,
            client_data={
                'playback_speed': playback_speed,
                'seek_count': seek_count,
                'pause_count': pause_count,
                'total_pause_duration': total_pause_duration,
                'elapsed_seconds': elapsed_seconds,
            },
        )
        
        # Anomali tespiti
        anomalies = cls._detect_anomalies(
            user, session, content, checks, playback_speed, seek_count, video_position
        )
        
        # Kullanıcı skorunu güncelle
        cls._update_user_score(user, check, anomalies)
        
        logger.info(
            f"Integrity check: user={user.id}, session={session.id}, "
            f"status={status}, score={overall_score:.2f}"
        )
        
        return check
    
    @classmethod
    def _check_visibility(cls, ratio: float) -> Dict:
        """Tab visibility kontrolü."""
        passed = ratio >= cls.DEFAULT_MIN_VISIBILITY
        return {
            'check': 'tab_visibility',
            'passed': passed,
            'value': ratio,
            'message': 'Tab aktif' if passed else 'Tab uzun süre pasif',
        }
    
    @classmethod
    def _check_playback_speed(cls, speed: float) -> Dict:
        """Playback speed kontrolü."""
        passed = speed <= cls.DEFAULT_MAX_SPEED
        # Skor: normal hızda 1.0, yüksek hızda düşük
        value = min(1.0, cls.DEFAULT_MAX_SPEED / max(speed, 0.25))
        return {
            'check': 'playback_speed',
            'passed': passed,
            'value': value,
            'detected_speed': speed,
            'message': 'Normal hız' if passed else f'Yüksek hız: {speed}x',
        }
    
    @classmethod
    def _check_seek_pattern(cls, seek_count: int, position: int, duration: int) -> Dict:
        """Seek pattern kontrolü."""
        if duration == 0:
            return {'check': 'seek_pattern', 'passed': True, 'value': 1.0}
        
        # Pozisyon/süre oranı - çok hızlı ilerleme kontrolü
        position_ratio = position / duration
        
        # Beklenen seek sayısı (dakikada ~1-2)
        expected_seeks = (position / 60) * 1.5
        seek_ratio = seek_count / max(expected_seeks, 1)
        
        # Aşırı seek = düşük skor
        passed = seek_ratio <= 3  # 3 katına kadar kabul
        value = min(1.0, 1.0 / max(seek_ratio, 0.1))
        
        return {
            'check': 'seek_pattern',
            'passed': passed,
            'value': value,
            'seek_count': seek_count,
            'message': 'Normal navigasyon' if passed else 'Aşırı atlama tespit edildi',
        }
    
    @classmethod
    def _check_timing_consistency(
        cls,
        elapsed_seconds: int,
        video_position: int,
        playback_speed: float,
        pause_duration: int,
    ) -> Dict:
        """Zamanlama tutarlılığı kontrolü."""
        # Beklenen video ilerlemesi
        effective_elapsed = elapsed_seconds - pause_duration
        expected_progress = effective_elapsed * playback_speed
        
        # Tolerans: %20
        tolerance = expected_progress * 0.2
        actual_progress = video_position
        
        diff = abs(actual_progress - expected_progress)
        passed = diff <= tolerance + 10  # +10 saniye buffer
        
        # Skor hesapla
        if expected_progress == 0:
            value = 1.0
        else:
            value = max(0, 1.0 - (diff / (expected_progress + 1)))
        
        return {
            'check': 'timing_consistency',
            'passed': passed,
            'value': value,
            'expected_progress': expected_progress,
            'actual_progress': actual_progress,
            'message': 'Zamanlama tutarlı' if passed else 'Zamanlama uyuşmazlığı',
        }
    
    # ============ Anomali Tespiti ============
    
    @classmethod
    def _detect_anomalies(
        cls,
        user,
        session: PlaybackSession,
        content: CourseContent,
        checks: List[Dict],
        playback_speed: float,
        seek_count: int,
        video_position: int,
    ) -> List[PlaybackAnomaly]:
        """Anomalileri tespit et ve kaydet."""
        anomalies = []
        
        # Hız manipülasyonu
        if playback_speed > 4:
            anomaly = cls._create_anomaly(
                user=user,
                session=session,
                content=content,
                anomaly_type=PlaybackAnomaly.AnomalyType.SPEED_MANIPULATION,
                severity=PlaybackAnomaly.AnomalySeverity.HIGH if playback_speed > 8 else PlaybackAnomaly.AnomalySeverity.MEDIUM,
                description=f"Anormal oynatma hızı tespit edildi: {playback_speed}x",
                details={'detected_speed': playback_speed},
                video_ts=video_position,
            )
            anomalies.append(anomaly)
        
        # Aşırı atlama
        duration = content.duration_minutes * 60
        if duration > 0 and seek_count > (duration / 30):  # 30 saniyede 1'den fazla
            anomaly = cls._create_anomaly(
                user=user,
                session=session,
                content=content,
                anomaly_type=PlaybackAnomaly.AnomalyType.EXCESSIVE_SEEKING,
                severity=PlaybackAnomaly.AnomalySeverity.MEDIUM,
                description=f"Aşırı atlama tespit edildi: {seek_count} seek",
                details={'seek_count': seek_count, 'duration': duration},
                video_ts=video_position,
            )
            anomalies.append(anomaly)
        
        # Tab inactive
        for check in checks:
            if check['check'] == 'tab_visibility' and not check['passed']:
                anomaly = cls._create_anomaly(
                    user=user,
                    session=session,
                    content=content,
                    anomaly_type=PlaybackAnomaly.AnomalyType.TAB_INACTIVE,
                    severity=PlaybackAnomaly.AnomalySeverity.LOW,
                    description=f"Tab uzun süre pasif: {check['value']:.0%}",
                    details={'visibility_ratio': check['value']},
                    video_ts=video_position,
                )
                anomalies.append(anomaly)
        
        return anomalies
    
    @classmethod
    def _create_anomaly(
        cls,
        user,
        session: PlaybackSession,
        content: CourseContent,
        anomaly_type: str,
        severity: str,
        description: str,
        details: Dict,
        video_ts: int = None,
    ) -> PlaybackAnomaly:
        """Anomali kaydı oluştur."""
        return PlaybackAnomaly.objects.create(
            tenant=user.tenant,
            session=session,
            user=user,
            content=content,
            anomaly_type=anomaly_type,
            severity=severity,
            description=description,
            details=details,
            video_ts=video_ts,
        )
    
    # ============ Cihaz Yönetimi ============
    
    @classmethod
    def get_or_create_device(cls, user, device_data: Dict) -> DeviceFingerprint:
        """Cihaz kaydını getir veya oluştur."""
        fingerprint_hash = device_data.get('fingerprint_hash', '')
        
        if not fingerprint_hash:
            # Fingerprint yoksa oluştur
            fingerprint_hash = hashlib.sha256(
                f"{device_data.get('user_agent', '')}"
                f"{device_data.get('screen_resolution', '')}"
                f"{device_data.get('timezone', '')}".encode()
            ).hexdigest()
        
        device, created = DeviceFingerprint.objects.get_or_create(
            tenant=user.tenant,
            user=user,
            fingerprint_hash=fingerprint_hash,
            defaults={
                'device_type': device_data.get('device_type', ''),
                'os': device_data.get('os', ''),
                'browser': device_data.get('browser', ''),
                'user_agent': device_data.get('user_agent', ''),
                'screen_resolution': device_data.get('screen_resolution', ''),
                'timezone': device_data.get('timezone', ''),
                'language': device_data.get('language', ''),
            }
        )
        
        if not created:
            device.session_count = F('session_count') + 1
            device.save(update_fields=['session_count', 'last_seen_at'])
        
        return device
    
    # ============ Skor Yönetimi ============
    
    @classmethod
    def get_or_create_user_score(cls, user) -> UserIntegrityScore:
        """Kullanıcı skorunu getir veya oluştur."""
        score, created = UserIntegrityScore.objects.get_or_create(
            user=user,
            tenant=user.tenant,
        )
        return score
    
    @classmethod
    @transaction.atomic
    def _update_user_score(
        cls,
        user,
        check: IntegrityCheck,
        anomalies: List[PlaybackAnomaly],
    ) -> UserIntegrityScore:
        """Kullanıcı skorunu güncelle."""
        user_score = cls.get_or_create_user_score(user)
        
        user_score.total_checks += 1
        
        if check.status == IntegrityCheck.CheckStatus.PASSED:
            user_score.passed_checks += 1
            # Skor artışı
            user_score.score = min(100, user_score.score + 1)
        else:
            user_score.failed_checks += 1
            # Skor düşüşü
            penalty = 5 if check.status == IntegrityCheck.CheckStatus.FAILED else 2
            user_score.score = max(0, user_score.score - penalty)
        
        # Anomali sayısı
        user_score.anomaly_count += len(anomalies)
        
        # Risk seviyesi güncelle
        if user_score.score < 30:
            user_score.risk_level = 'high'
        elif user_score.score < 60:
            user_score.risk_level = 'medium'
        else:
            user_score.risk_level = 'low'
        
        # Otomatik kısıtlama
        config = cls.get_config(user.tenant)
        if user_score.score < config.auto_restrict_threshold and not user_score.is_restricted:
            user_score.is_restricted = True
            user_score.restriction_reason = f"Bütünlük skoru eşiğin altına düştü: {user_score.score}"
            user_score.restricted_at = timezone.now()
        
        user_score.last_check_at = timezone.now()
        user_score.save()
        
        return user_score
    
    # ============ Durum Sorgulama ============
    
    @classmethod
    def get_user_status(cls, user) -> Dict:
        """Kullanıcının bütünlük durumunu getir."""
        user_score = cls.get_or_create_user_score(user)
        
        recent_anomalies = PlaybackAnomaly.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timezone.timedelta(days=7),
        ).count()
        
        return {
            'user_score': user_score.score,
            'risk_level': user_score.risk_level,
            'is_restricted': user_score.is_restricted,
            'total_checks': user_score.total_checks,
            'pass_rate': user_score.pass_rate,
            'recent_anomalies': recent_anomalies,
            'last_check_at': user_score.last_check_at,
        }
    
    # ============ Yapılandırma ============
    
    @classmethod
    def get_config(cls, tenant) -> IntegrityConfig:
        """Tenant yapılandırmasını getir."""
        config, created = IntegrityConfig.objects.get_or_create(
            tenant=tenant,
            defaults={
                'min_visibility_score': cls.DEFAULT_MIN_VISIBILITY,
                'min_playback_score': cls.DEFAULT_MIN_PLAYBACK,
                'min_overall_score': cls.DEFAULT_MIN_OVERALL,
            }
        )
        return config

