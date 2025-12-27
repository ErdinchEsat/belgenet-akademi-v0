"""
Recommendation Service
======================

Öneri sistemi iş mantığı.
"""

import logging
from typing import List, Dict, Optional
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from backend.courses.models import Course, CourseContent
from backend.progress.models import VideoProgress
from ..models import (
    UserContentInterest,
    ContentSimilarity,
    Recommendation,
    RecommendationFeedback,
    TrendingContent,
)

logger = logging.getLogger(__name__)


class RecommendationService:
    """
    Öneri sistemi servisi.
    
    Sorumluluklar:
    - Kişiselleştirilmiş öneriler
    - Benzer içerik önerileri
    - Trend içerikler
    - Sonraki içerik önerisi
    - Geri bildirim işleme
    """
    
    # ============ Kişiselleştirilmiş Öneriler ============
    
    @classmethod
    def get_personalized_recommendations(
        cls,
        user,
        limit: int = 10,
        exclude_completed: bool = True,
        exclude_in_progress: bool = False,
    ) -> List[Dict]:
        """
        Kullanıcı için kişiselleştirilmiş öneriler getir.
        
        TODO: Gerçek ML modeli entegrasyonu
        """
        # Kullanıcının tamamladığı içerikleri al
        completed_content_ids = []
        in_progress_content_ids = []
        
        if exclude_completed or exclude_in_progress:
            progresses = VideoProgress.objects.filter(user=user)
            
            if exclude_completed:
                completed_content_ids = list(
                    progresses.filter(is_completed=True)
                    .values_list('content_id', flat=True)
                )
            
            if exclude_in_progress:
                in_progress_content_ids = list(
                    progresses.filter(is_completed=False, watched_seconds__gt=0)
                    .values_list('content_id', flat=True)
                )
        
        exclude_ids = set(completed_content_ids + in_progress_content_ids)
        
        # Kullanıcının ilgi profilini al
        interest = cls.get_or_create_interest_profile(user)
        
        # Basit öneri: En çok izlenen kategorilerden içerik öner
        # TODO: ML model ile değiştir
        contents = CourseContent.objects.filter(
            module__course__tenant=user.tenant,
            module__course__is_published=True,
        ).exclude(
            id__in=exclude_ids
        ).select_related(
            'module__course'
        ).order_by('?')[:limit]  # Şimdilik rastgele
        
        recommendations = []
        for i, content in enumerate(contents):
            # Öneri kaydı oluştur
            rec = Recommendation.objects.create(
                tenant=user.tenant,
                user=user,
                content=content,
                course=content.module.course,
                recommendation_type=Recommendation.RecommendationType.PERSONALIZED,
                score=1.0 - (i * 0.1),  # Mock skor
                rank=i + 1,
                reason=cls._generate_reason(content, interest),
                model_version='mock-v1',
            )
            
            recommendations.append({
                'recommendation_id': rec.id,
                'content_id': content.id,
                'course_id': content.module.course.id,
                'title': content.title,
                'description': content.description or '',
                'thumbnail_url': getattr(content, 'thumbnail_url', None),
                'duration_minutes': content.duration_minutes,
                'instructor_name': content.module.course.instructor.full_name if content.module.course.instructor else '',
                'recommendation_type': rec.recommendation_type,
                'score': rec.score,
                'rank': rec.rank,
                'reason': rec.reason,
            })
        
        return recommendations
    
    @classmethod
    def _generate_reason(cls, content: CourseContent, interest: UserContentInterest) -> str:
        """Öneri nedeni oluştur."""
        # Mock neden oluşturma
        reasons = [
            f"'{content.module.course.title}' kursundan popüler bir içerik",
            "İzleme geçmişinize göre ilginizi çekebilir",
            "Bu kategoride yüksek puan almış bir içerik",
            "Benzer kullanıcılar tarafından beğenildi",
        ]
        import random
        return random.choice(reasons)
    
    # ============ Sonraki İçerik Önerisi ============
    
    @classmethod
    def get_next_content(
        cls,
        user,
        current_content: CourseContent,
    ) -> Optional[Dict]:
        """
        Mevcut içerikten sonra izlenecek içeriği öner.
        """
        course = current_content.module.course
        module = current_content.module
        
        # 1. Aynı modüldeki sonraki içerik
        next_in_module = CourseContent.objects.filter(
            module=module,
            order__gt=current_content.order,
        ).order_by('order').first()
        
        if next_in_module:
            return {
                'content_id': next_in_module.id,
                'course_id': course.id,
                'title': next_in_module.title,
                'description': next_in_module.description or '',
                'duration_minutes': next_in_module.duration_minutes,
                'reason': f"'{module.title}' modülünde sıradaki içerik",
                'auto_play': True,
            }
        
        # 2. Sonraki modülün ilk içeriği
        from backend.courses.models import CourseModule
        next_module = CourseModule.objects.filter(
            course=course,
            order__gt=module.order,
        ).order_by('order').first()
        
        if next_module:
            first_content = CourseContent.objects.filter(
                module=next_module,
            ).order_by('order').first()
            
            if first_content:
                return {
                    'content_id': first_content.id,
                    'course_id': course.id,
                    'title': first_content.title,
                    'description': first_content.description or '',
                    'duration_minutes': first_content.duration_minutes,
                    'reason': f"'{next_module.title}' modülüne geç",
                    'auto_play': False,
                }
        
        # 3. Kurs tamamlandı, benzer kurs öner
        similar = cls.get_similar_content(user, current_content, limit=1)
        if similar:
            return {
                'content_id': similar[0]['content_id'],
                'course_id': similar[0]['course_id'],
                'title': similar[0]['title'],
                'description': '',
                'duration_minutes': similar[0]['duration_minutes'],
                'reason': 'Kursu tamamladınız! Benzer bir içerik öneriyoruz.',
                'auto_play': False,
            }
        
        return None
    
    # ============ Benzer İçerikler ============
    
    @classmethod
    def get_similar_content(
        cls,
        user,
        content: CourseContent,
        limit: int = 5,
    ) -> List[Dict]:
        """
        İçeriğe benzer içerikleri getir.
        """
        # Pre-computed benzerliklerden al
        similarities = ContentSimilarity.objects.filter(
            Q(content_a=content) | Q(content_b=content),
        ).order_by('-similarity_score')[:limit]
        
        result = []
        for sim in similarities:
            similar_content = sim.content_b if sim.content_a == content else sim.content_a
            
            result.append({
                'content_id': similar_content.id,
                'course_id': similar_content.module.course.id,
                'title': similar_content.title,
                'thumbnail_url': getattr(similar_content, 'thumbnail_url', None),
                'duration_minutes': similar_content.duration_minutes,
                'similarity_score': sim.similarity_score,
            })
        
        # Eğer pre-computed yoksa, aynı kategoriden öner
        if not result:
            same_category = CourseContent.objects.filter(
                module__course__tenant=user.tenant,
                module__course__is_published=True,
            ).exclude(
                id=content.id
            ).select_related(
                'module__course'
            ).order_by('?')[:limit]
            
            for c in same_category:
                result.append({
                    'content_id': c.id,
                    'course_id': c.module.course.id,
                    'title': c.title,
                    'thumbnail_url': getattr(c, 'thumbnail_url', None),
                    'duration_minutes': c.duration_minutes,
                    'similarity_score': 0.5,  # Mock
                })
        
        return result
    
    # ============ Trend İçerikler ============
    
    @classmethod
    def get_trending_content(
        cls,
        user,
        period: str = TrendingContent.TrendPeriod.WEEKLY,
        limit: int = 10,
    ) -> List[TrendingContent]:
        """
        Trend içerikleri getir.
        """
        return list(
            TrendingContent.objects.filter(
                tenant=user.tenant,
                period=period,
            ).select_related(
                'content__module__course'
            ).order_by('rank')[:limit]
        )
    
    # ============ Geri Bildirim ============
    
    @classmethod
    @transaction.atomic
    def record_feedback(
        cls,
        user,
        recommendation_id: str,
        feedback_type: str,
        comment: str = '',
    ) -> RecommendationFeedback:
        """
        Öneri geri bildirimi kaydet.
        """
        recommendation = Recommendation.objects.get(
            id=recommendation_id,
            user=user,
        )
        
        feedback, created = RecommendationFeedback.objects.update_or_create(
            tenant=user.tenant,
            recommendation=recommendation,
            user=user,
            defaults={
                'feedback_type': feedback_type,
                'comment': comment,
            }
        )
        
        # Dismissed durumu güncelle
        if feedback_type in ['not_interested', 'wrong_topic']:
            recommendation.status = Recommendation.RecommendationStatus.DISMISSED
            recommendation.save()
        
        logger.info(
            f"Recommendation feedback: user={user.id}, "
            f"rec={recommendation_id}, type={feedback_type}"
        )
        
        return feedback
    
    @classmethod
    @transaction.atomic
    def record_click(
        cls,
        user,
        recommendation_id: str,
    ) -> Recommendation:
        """
        Öneri tıklamasını kaydet.
        """
        recommendation = Recommendation.objects.get(
            id=recommendation_id,
            user=user,
        )
        
        recommendation.status = Recommendation.RecommendationStatus.CLICKED
        recommendation.clicked_at = timezone.now()
        recommendation.save()
        
        return recommendation
    
    # ============ İlgi Profili ============
    
    @classmethod
    def get_or_create_interest_profile(cls, user) -> UserContentInterest:
        """
        Kullanıcı ilgi profilini getir veya oluştur.
        """
        interest, created = UserContentInterest.objects.get_or_create(
            user=user,
            tenant=user.tenant,
        )
        return interest
    
    @classmethod
    @transaction.atomic
    def update_interest_profile(
        cls,
        user,
        content: CourseContent,
        watch_time: int = 0,
        completed: bool = False,
    ) -> UserContentInterest:
        """
        İçerik izleme sonrası ilgi profilini güncelle.
        """
        interest = cls.get_or_create_interest_profile(user)
        
        # İzleme süresini güncelle
        interest.total_watch_time += watch_time
        
        # Tamamlama sayısını güncelle
        if completed:
            interest.total_completions += 1
        
        # Aktif saati güncelle
        current_hour = str(timezone.now().hour)
        if current_hour in interest.active_hours:
            interest.active_hours[current_hour] += 1
        else:
            interest.active_hours[current_hour] = 1
        
        # TODO: Kategori ve etiket skorlarını güncelle
        # Bu kısım kursun kategorisine ve etiketlerine bağlı
        
        interest.last_activity_at = timezone.now()
        interest.save()
        
        return interest
    
    # ============ Devam Et Önerileri ============
    
    @classmethod
    def get_continue_watching(
        cls,
        user,
        limit: int = 5,
    ) -> List[Dict]:
        """
        Yarıda kalan içerikleri getir.
        """
        in_progress = VideoProgress.objects.filter(
            user=user,
            is_completed=False,
            watched_seconds__gt=0,
        ).select_related(
            'content__module__course'
        ).order_by('-updated_at')[:limit]
        
        result = []
        for progress in in_progress:
            content = progress.content
            result.append({
                'content_id': content.id,
                'course_id': content.module.course.id,
                'title': content.title,
                'thumbnail_url': getattr(content, 'thumbnail_url', None),
                'duration_minutes': content.duration_minutes,
                'progress_percent': int(progress.completion_ratio * 100),
                'last_position': progress.last_position_seconds,
            })
        
        return result

