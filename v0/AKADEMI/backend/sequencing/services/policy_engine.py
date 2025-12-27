"""
Policy Engine
=============

İçerik kilitleme policy değerlendirme motoru.
"""

import logging
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from backend.courses.models import Course, CourseContent, Enrollment
from backend.progress.models import VideoProgress
from ..models import ContentLockPolicy, ContentUnlockState

logger = logging.getLogger(__name__)


class PolicyEngine:
    """
    İçerik kilitleme policy motoru.
    
    Sorumluluklar:
    - Policy değerlendirme
    - Unlock state yönetimi
    - Gereksinim hesaplama
    """
    
    @classmethod
    def get_lock_status(
        cls,
        user,
        course: Course,
        content: CourseContent,
    ) -> Tuple[bool, List[Dict]]:
        """
        İçerik kilit durumunu getir.
        
        Args:
            user: Kullanıcı
            course: Kurs
            content: İçerik
        
        Returns:
            Tuple[is_unlocked, requirements]: (Açık mı?, Gereksinimler listesi)
        """
        # Unlock state'i al
        unlock_state = cls._get_or_create_unlock_state(user, course, content)
        
        # Eğer zaten açıksa, gereksinimleri evaluation_state'den al
        if unlock_state.is_unlocked:
            requirements = cls._state_to_requirements(unlock_state.evaluation_state)
            return True, requirements
        
        # Policy'leri al
        policies = ContentLockPolicy.objects.filter(
            tenant=user.tenant,
            content=content,
            is_active=True,
        ).order_by('-priority')
        
        # Policy yoksa varsayılan olarak açık
        if not policies.exists():
            # İlk içerik mi kontrol et
            if cls._is_first_content(content):
                return True, []
            
            # Önceki içerik tamamlanmalı (varsayılan)
            prev_completed = cls._check_previous_completed(user, content)
            if prev_completed:
                return True, []
            return False, [{
                'type': 'requires_prev_completed',
                'passed': False,
                'details': {'message': 'Önceki içerik tamamlanmalı'},
            }]
        
        # Her policy'yi değerlendir
        requirements = []
        all_passed = True
        
        for policy in policies:
            passed, details = cls._evaluate_policy(user, course, content, policy)
            requirements.append({
                'type': policy.policy_type,
                'passed': passed,
                'details': details,
            })
            if not passed:
                all_passed = False
        
        return all_passed, requirements
    
    @classmethod
    @transaction.atomic
    def evaluate_unlock(
        cls,
        user,
        course: Course,
        content: CourseContent,
    ) -> Tuple[bool, bool]:
        """
        Kilit değerlendirmesi yap ve güncelle.
        
        Args:
            user: Kullanıcı
            course: Kurs
            content: İçerik
        
        Returns:
            Tuple[is_unlocked, changed]: (Açık mı?, Durum değişti mi?)
        """
        unlock_state = cls._get_or_create_unlock_state(user, course, content)
        was_unlocked = unlock_state.is_unlocked
        
        # Değerlendirme yap
        is_unlocked, requirements = cls.get_lock_status(user, course, content)
        
        # State güncelle
        unlock_state.evaluation_state = cls._requirements_to_state(requirements)
        unlock_state.last_evaluated_at = timezone.now()
        
        if is_unlocked and not was_unlocked:
            unlock_state.is_unlocked = True
            unlock_state.unlocked_at = timezone.now()
            unlock_state.unlock_reason = 'policy_passed'
            logger.info(f"Content unlocked: user={user.id}, content={content.id}")
        
        unlock_state.save()
        
        changed = is_unlocked != was_unlocked
        return is_unlocked, changed
    
    @classmethod
    def _get_or_create_unlock_state(
        cls,
        user,
        course: Course,
        content: CourseContent,
    ) -> ContentUnlockState:
        """Unlock state'i getir veya oluştur."""
        state, created = ContentUnlockState.objects.get_or_create(
            tenant=user.tenant,
            user=user,
            content=content,
            defaults={
                'course': course,
                'is_unlocked': False,
                'evaluation_state': {},
            }
        )
        return state
    
    @classmethod
    def _evaluate_policy(
        cls,
        user,
        course: Course,
        content: CourseContent,
        policy: ContentLockPolicy,
    ) -> Tuple[bool, Dict]:
        """
        Tek bir policy'yi değerlendir.
        
        Returns:
            Tuple[passed, details]
        """
        policy_type = policy.policy_type
        config = policy.policy_config
        
        if policy_type == ContentLockPolicy.PolicyType.MIN_WATCH_RATIO:
            return cls._check_min_watch_ratio(user, content, config)
        
        elif policy_type == ContentLockPolicy.PolicyType.REQUIRES_PREV_COMPLETED:
            return cls._check_requires_prev_completed(user, content, config)
        
        elif policy_type == ContentLockPolicy.PolicyType.REQUIRES_QUIZ_PASS:
            return cls._check_requires_quiz_pass(user, content, config)
        
        elif policy_type == ContentLockPolicy.PolicyType.TIME_LOCKED:
            return cls._check_time_locked(config)
        
        # Bilinmeyen policy type
        logger.warning(f"Unknown policy type: {policy_type}")
        return True, {'message': 'Unknown policy'}
    
    @classmethod
    def _check_min_watch_ratio(
        cls,
        user,
        content: CourseContent,
        config: Dict,
    ) -> Tuple[bool, Dict]:
        """Minimum izleme oranı kontrolü."""
        min_ratio = config.get('min_ratio', 0.8)
        
        try:
            progress = VideoProgress.objects.get(
                tenant=user.tenant,
                user=user,
                content=content,
            )
            current_ratio = float(progress.completion_ratio)
        except VideoProgress.DoesNotExist:
            current_ratio = 0.0
        
        passed = current_ratio >= min_ratio
        
        return passed, {
            'current': round(current_ratio, 4),
            'required': min_ratio,
        }
    
    @classmethod
    def _check_requires_prev_completed(
        cls,
        user,
        content: CourseContent,
        config: Dict,
    ) -> Tuple[bool, Dict]:
        """Önceki içerik tamamlanmalı kontrolü."""
        prev_content_id = config.get('prev_content_id')
        
        if prev_content_id:
            # Belirli içerik
            try:
                prev_content = CourseContent.objects.get(id=prev_content_id)
            except CourseContent.DoesNotExist:
                return True, {'message': 'Previous content not found'}
        else:
            # Sıradaki önceki içerik
            prev_content = cls._get_previous_content(content)
            if not prev_content:
                return True, {'message': 'No previous content'}
        
        # Önceki içerik tamamlandı mı?
        try:
            prev_progress = VideoProgress.objects.get(
                tenant=user.tenant,
                user=user,
                content=prev_content,
            )
            completed = prev_progress.is_completed
        except VideoProgress.DoesNotExist:
            completed = False
        
        return completed, {
            'prev_content_id': prev_content.id,
            'prev_content_title': prev_content.title,
            'completed': completed,
        }
    
    @classmethod
    def _check_requires_quiz_pass(
        cls,
        user,
        content: CourseContent,
        config: Dict,
    ) -> Tuple[bool, Dict]:
        """Quiz geçilmeli kontrolü."""
        quiz_id = config.get('quiz_id')
        min_score = config.get('min_score', 70)
        
        if not quiz_id:
            return True, {'message': 'Quiz not configured'}
        
        # Quiz attempt kontrolü (quizzes app'i daha sonra implemente edilecek)
        # Şimdilik placeholder
        # TODO: QuizAttempt modelinden kontrol et
        
        return False, {
            'quiz_id': quiz_id,
            'min_score': min_score,
            'passed': False,
            'score': None,
        }
    
    @classmethod
    def _check_time_locked(cls, config: Dict) -> Tuple[bool, Dict]:
        """Zamana bağlı kilit kontrolü."""
        unlock_after = config.get('unlock_after')
        
        if not unlock_after:
            return True, {'message': 'Unlock time not configured'}
        
        try:
            from django.utils.dateparse import parse_datetime
            unlock_time = parse_datetime(unlock_after)
            if unlock_time and timezone.now() >= unlock_time:
                return True, {'unlock_after': unlock_after, 'unlocked': True}
            return False, {'unlock_after': unlock_after, 'unlocked': False}
        except Exception:
            return True, {'message': 'Invalid unlock time'}
    
    @classmethod
    def _is_first_content(cls, content: CourseContent) -> bool:
        """İçerik modüldeki ilk içerik mi?"""
        first_content = CourseContent.objects.filter(
            module=content.module
        ).order_by('order').first()
        return first_content and first_content.id == content.id
    
    @classmethod
    def _get_previous_content(cls, content: CourseContent) -> Optional[CourseContent]:
        """Önceki içeriği getir."""
        # Aynı modüldeki önceki
        prev_in_module = CourseContent.objects.filter(
            module=content.module,
            order__lt=content.order,
        ).order_by('-order').first()
        
        if prev_in_module:
            return prev_in_module
        
        # Önceki modülün son içeriği
        prev_module = content.module.course.modules.filter(
            order__lt=content.module.order
        ).order_by('-order').first()
        
        if prev_module:
            return prev_module.contents.order_by('-order').first()
        
        return None
    
    @classmethod
    def _check_previous_completed(cls, user, content: CourseContent) -> bool:
        """Önceki içerik tamamlandı mı?"""
        prev_content = cls._get_previous_content(content)
        if not prev_content:
            return True
        
        try:
            prev_progress = VideoProgress.objects.get(
                tenant=user.tenant,
                user=user,
                content=prev_content,
            )
            return prev_progress.is_completed
        except VideoProgress.DoesNotExist:
            return False
    
    @staticmethod
    def _requirements_to_state(requirements: List[Dict]) -> Dict:
        """Requirements listesini state dict'e dönüştür."""
        return {r['type']: r for r in requirements}
    
    @staticmethod
    def _state_to_requirements(state: Dict) -> List[Dict]:
        """State dict'i requirements listesine dönüştür."""
        return list(state.values()) if state else []

