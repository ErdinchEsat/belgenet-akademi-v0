"""
Grading Service
===============

Quiz notlandırma servisi.
"""

import logging
from typing import List, Dict, Tuple
from django.utils import timezone
from django.db import transaction

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession
from ..models import Quiz, QuizQuestion, QuizAttempt, QuizAnswer

logger = logging.getLogger(__name__)


class GradingService:
    """
    Quiz notlandırma servisi.
    
    Sorumluluklar:
    - Attempt oluşturma
    - Cevap kaydetme
    - Notlandırma
    - Policy tetikleme
    """
    
    @classmethod
    @transaction.atomic
    def start_attempt(
        cls,
        user,
        quiz: Quiz,
        course: Course = None,
        content: CourseContent = None,
        session: PlaybackSession = None,
    ) -> QuizAttempt:
        """
        Quiz denemesi başlat.
        
        Args:
            user: Kullanıcı
            quiz: Quiz
            course: Kurs (opsiyonel)
            content: İçerik (opsiyonel)
            session: Playback session (opsiyonel)
        
        Returns:
            QuizAttempt
        """
        # Maksimum deneme kontrolü
        if quiz.max_attempts > 0:
            attempt_count = QuizAttempt.objects.filter(
                quiz=quiz,
                user=user,
                status__in=[QuizAttempt.Status.SUBMITTED, QuizAttempt.Status.GRADED],
            ).count()
            
            if attempt_count >= quiz.max_attempts:
                raise ValueError(f"Maksimum deneme sayısına ({quiz.max_attempts}) ulaşıldı")
        
        # Süre limiti hesapla
        expires_at = None
        if quiz.time_limit_minutes:
            expires_at = timezone.now() + timezone.timedelta(minutes=quiz.time_limit_minutes)
        
        # Attempt oluştur
        attempt = QuizAttempt.objects.create(
            tenant=user.tenant,
            quiz=quiz,
            user=user,
            course=course or quiz.course,
            content=content or quiz.content,
            session=session,
            status=QuizAttempt.Status.STARTED,
            max_score=quiz.total_points,
            expires_at=expires_at,
        )
        
        logger.info(f"Quiz attempt started: {attempt.id} for user {user.id}")
        
        return attempt
    
    @classmethod
    @transaction.atomic
    def submit_answers(
        cls,
        attempt: QuizAttempt,
        answers: List[Dict],
    ) -> QuizAttempt:
        """
        Cevapları kaydet ve notlandır.
        
        Args:
            attempt: Quiz denemesi
            answers: Cevap listesi [{"question_id": uuid, "answer": ...}, ...]
        
        Returns:
            Notlandırılmış QuizAttempt
        """
        # Süre kontrolü
        if attempt.is_expired:
            attempt.status = QuizAttempt.Status.EXPIRED
            attempt.save(update_fields=['status', 'updated_at'])
            raise ValueError("Quiz süresi doldu")
        
        # Zaten gönderilmiş mi?
        if attempt.status in [QuizAttempt.Status.SUBMITTED, QuizAttempt.Status.GRADED]:
            raise ValueError("Bu deneme zaten gönderilmiş")
        
        # Cevapları kaydet
        for answer_data in answers:
            question_id = answer_data['question_id']
            answer_value = answer_data['answer']
            
            try:
                question = attempt.quiz.questions.get(id=question_id)
            except QuizQuestion.DoesNotExist:
                logger.warning(f"Question not found: {question_id}")
                continue
            
            # Mevcut cevabı güncelle veya oluştur
            quiz_answer, created = QuizAnswer.objects.update_or_create(
                tenant=attempt.tenant,
                attempt=attempt,
                question=question,
                defaults={
                    'answer': answer_value,
                }
            )
            
            # Notlandır
            quiz_answer.grade()
        
        # Toplam puanı hesapla
        attempt.calculate_score()
        
        # Durumu güncelle
        attempt.status = QuizAttempt.Status.GRADED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=['status', 'submitted_at', 'updated_at'])
        
        logger.info(
            f"Quiz submitted: attempt={attempt.id}, score={attempt.score}/{attempt.max_score}, "
            f"passed={attempt.passed}"
        )
        
        # Sequencing policy tetikle (eğer blocking quiz ise)
        if attempt.quiz.is_blocking and attempt.passed:
            cls._trigger_policy_evaluation(attempt)
        
        return attempt
    
    @classmethod
    def _trigger_policy_evaluation(cls, attempt: QuizAttempt):
        """Sequencing policy değerlendirmesini tetikle."""
        if not attempt.content:
            return
        
        try:
            from backend.sequencing.services import PolicyEngine
            
            # Sonraki içerik için değerlendirme yap
            next_content = cls._get_next_content(attempt.content)
            if next_content:
                PolicyEngine.evaluate_unlock(
                    user=attempt.user,
                    course=attempt.course,
                    content=next_content,
                )
                logger.info(f"Policy evaluation triggered for content {next_content.id}")
                
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
    
    @staticmethod
    def _get_next_content(content: CourseContent):
        """Sonraki içeriği getir."""
        # Aynı modüldeki sonraki
        next_in_module = CourseContent.objects.filter(
            module=content.module,
            order__gt=content.order,
        ).order_by('order').first()
        
        if next_in_module:
            return next_in_module
        
        # Sonraki modülün ilk içeriği
        next_module = content.module.course.modules.filter(
            order__gt=content.module.order
        ).order_by('order').first()
        
        if next_module:
            return next_module.contents.order_by('order').first()
        
        return None
    
    @classmethod
    def get_attempt_result(cls, attempt: QuizAttempt) -> Dict:
        """Attempt sonuçlarını getir."""
        answers = []
        
        for answer in attempt.answers.select_related('question').order_by('question__order'):
            answer_data = {
                'question_id': str(answer.question.id),
                'question_type': answer.question.question_type,
                'prompt': answer.question.prompt,
                'options': answer.question.options,
                'user_answer': answer.answer,
                'is_correct': answer.is_correct,
                'points_awarded': float(answer.points_awarded),
                'max_points': float(answer.question.points),
            }
            
            # Eşleştirme soruları için kısmi doğruluk bilgisi
            if answer.question.question_type == 'matching':
                answer_data['partial_score'] = answer.question.get_matching_score(answer.answer)
                answer_data['matching_details'] = cls._get_matching_details(
                    answer.question, 
                    answer.answer, 
                    attempt.quiz.show_correct_answers
                )
            
            # Doğru cevapları göster (ayara göre)
            if attempt.quiz.show_correct_answers:
                answer_data['correct_answer'] = answer.question.correct_answer
                answer_data['explanation'] = answer.question.explanation
            
            answers.append(answer_data)
        
        return {
            'attempt_id': str(attempt.id),
            'score': float(attempt.score),
            'max_score': float(attempt.max_score),
            'score_percent': attempt.score_percent,
            'passed': attempt.passed,
            'answers': answers,
        }
    
    @classmethod
    def _get_matching_details(cls, question, user_answer: Dict, show_correct: bool) -> List[Dict]:
        """
        Eşleştirme sorusu için detaylı sonuç.
        
        Returns:
            [
                {
                    "left_index": 0,
                    "left_text": "Başkent",
                    "user_right_index": 1,
                    "user_right_text": "Türkçe",
                    "is_correct": false,
                    "correct_right_index": 0,  # show_correct=True ise
                    "correct_right_text": "Ankara"  # show_correct=True ise
                },
                ...
            ]
        """
        if not isinstance(question.options, dict):
            return []
        
        left_items = question.options.get('left', [])
        right_items = question.options.get('right', [])
        correct_answer = question.correct_answer or {}
        user_answer = user_answer or {}
        
        details = []
        
        for left_idx, left_text in enumerate(left_items):
            left_key = str(left_idx)
            user_right_idx = user_answer.get(left_key)
            correct_right_idx = correct_answer.get(left_key)
            
            detail = {
                'left_index': left_idx,
                'left_text': left_text,
                'user_right_index': int(user_right_idx) if user_right_idx is not None else None,
                'user_right_text': right_items[int(user_right_idx)] if user_right_idx is not None and int(user_right_idx) < len(right_items) else None,
                'is_correct': str(user_right_idx) == str(correct_right_idx) if user_right_idx is not None else False,
            }
            
            if show_correct and correct_right_idx is not None:
                detail['correct_right_index'] = int(correct_right_idx)
                detail['correct_right_text'] = right_items[int(correct_right_idx)] if int(correct_right_idx) < len(right_items) else None
            
            details.append(detail)
        
        return details

