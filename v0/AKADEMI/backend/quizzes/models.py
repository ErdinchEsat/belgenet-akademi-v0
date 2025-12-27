"""
Quizzes Models
==============

Quiz sistemi modelleri.
"""

import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend.libs.tenant_aware.models import TenantAwareModel


class Quiz(TenantAwareModel):
    """
    Quiz tanımı.
    
    Bir içeriğe bağlı veya bağımsız olabilir.
    Video içi quiz'ler için content ve timecode kullanılır.
    """
    
    title = models.CharField(
        _('Başlık'),
        max_length=200,
    )
    
    description = models.TextField(
        _('Açıklama'),
        blank=True,
    )
    
    # İlişkiler (opsiyonel - video içi quiz için)
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='quizzes',
        verbose_name=_('Kurs'),
        null=True,
        blank=True,
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='quizzes',
        verbose_name=_('İçerik'),
        null=True,
        blank=True,
        help_text=_('Video içi quiz için'),
    )
    
    # Video içi quiz için timecode
    video_timecode = models.PositiveIntegerField(
        _('Video Zamanı (sn)'),
        null=True,
        blank=True,
        help_text=_('Quiz\'in gösterileceği video zamanı'),
    )
    
    # Geçme kriterleri
    passing_score = models.DecimalField(
        _('Geçme Puanı'),
        max_digits=5,
        decimal_places=2,
        default=70,
        help_text=_('Minimum geçme puanı (0-100)'),
    )
    
    # Quiz ayarları
    time_limit_minutes = models.PositiveIntegerField(
        _('Süre Limiti (dk)'),
        null=True,
        blank=True,
        help_text=_('Boş bırakılırsa süresiz'),
    )
    
    max_attempts = models.PositiveIntegerField(
        _('Maksimum Deneme'),
        default=0,
        help_text=_('0 = sınırsız'),
    )
    
    shuffle_questions = models.BooleanField(
        _('Soruları Karıştır'),
        default=False,
    )
    
    shuffle_options = models.BooleanField(
        _('Seçenekleri Karıştır'),
        default=False,
    )
    
    show_correct_answers = models.BooleanField(
        _('Doğru Cevapları Göster'),
        default=True,
        help_text=_('Quiz bittikten sonra'),
    )
    
    is_blocking = models.BooleanField(
        _('İlerlemeyi Engeller'),
        default=False,
        help_text=_('Geçilmeden sonraki içerik açılmaz'),
    )
    
    is_active = models.BooleanField(
        _('Aktif'),
        default=True,
    )
    
    class Meta:
        verbose_name = _('Quiz')
        verbose_name_plural = _('Quiz\'ler')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'course']),
            models.Index(fields=['tenant', 'content']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def question_count(self) -> int:
        return self.questions.count()
    
    @property
    def total_points(self) -> float:
        return sum(q.points for q in self.questions.all())


class QuizQuestion(TenantAwareModel):
    """
    Quiz sorusu.
    
    Soru türleri:
    - mcq: Çoktan seçmeli (tek cevap)
    - multi: Çoklu seçim
    - truefalse: Doğru/Yanlış
    - short: Kısa cevap
    - matching: Eşleştirme
    
    Eşleştirme Sorusu Formatı:
    -------------------------
    options: {
        "left": ["Sol 1", "Sol 2", "Sol 3"],
        "right": ["Sağ A", "Sağ B", "Sağ C"]
    }
    correct_answer: {
        "0": "1",  # Sol 1 -> Sağ B (index 1)
        "1": "2",  # Sol 2 -> Sağ C (index 2)
        "2": "0"   # Sol 3 -> Sağ A (index 0)
    }
    
    Kullanıcı cevabı:
    answer: {
        "0": "1",  # Kullanıcının eşleştirmesi
        "1": "2",
        "2": "0"
    }
    """
    
    class QuestionType(models.TextChoices):
        MCQ = 'mcq', _('Çoktan Seçmeli')
        MULTI = 'multi', _('Çoklu Seçim')
        TRUE_FALSE = 'truefalse', _('Doğru/Yanlış')
        SHORT = 'short', _('Kısa Cevap')
        MATCHING = 'matching', _('Eşleştirme')
    
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name=_('Quiz'),
    )
    
    question_type = models.CharField(
        _('Soru Türü'),
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.MCQ,
    )
    
    prompt = models.TextField(
        _('Soru'),
    )
    
    # Seçenekler (mcq, multi için)
    options = models.JSONField(
        _('Seçenekler'),
        default=list,
        blank=True,
        help_text=_('["A seçeneği", "B seçeneği", ...]'),
    )
    
    # Doğru cevap
    correct_answer = models.JSONField(
        _('Doğru Cevap'),
        help_text=_('mcq: "A", multi: ["A", "B"], truefalse: true/false, short: "cevap"'),
    )
    
    # Açıklama (cevap sonrası gösterilir)
    explanation = models.TextField(
        _('Açıklama'),
        blank=True,
        help_text=_('Cevap sonrası gösterilen açıklama'),
    )
    
    # Puanlama
    points = models.DecimalField(
        _('Puan'),
        max_digits=5,
        decimal_places=2,
        default=1,
    )
    
    # Sıralama
    order = models.PositiveIntegerField(
        _('Sıra'),
        default=0,
    )
    
    class Meta:
        verbose_name = _('Quiz Sorusu')
        verbose_name_plural = _('Quiz Soruları')
        ordering = ['order']
        indexes = [
            models.Index(fields=['quiz', 'order']),
        ]
    
    def __str__(self):
        return f"{self.quiz.title} - Q{self.order + 1}"
    
    def check_answer(self, answer) -> bool:
        """Cevabın doğru olup olmadığını kontrol et."""
        correct = self.correct_answer
        
        if self.question_type == self.QuestionType.MCQ:
            return str(answer).upper() == str(correct).upper()
        
        elif self.question_type == self.QuestionType.MULTI:
            if not isinstance(answer, list):
                return False
            return set(str(a).upper() for a in answer) == set(str(c).upper() for c in correct)
        
        elif self.question_type == self.QuestionType.TRUE_FALSE:
            return bool(answer) == bool(correct)
        
        elif self.question_type == self.QuestionType.SHORT:
            return str(answer).strip().lower() == str(correct).strip().lower()
        
        elif self.question_type == self.QuestionType.MATCHING:
            return self._check_matching_answer(answer, correct)
        
        return False
    
    def _check_matching_answer(self, answer, correct) -> bool:
        """
        Eşleştirme cevabını kontrol et.
        
        Args:
            answer: Kullanıcı cevabı {"0": "1", "1": "2", ...}
            correct: Doğru cevap {"0": "1", "1": "2", ...}
        
        Returns:
            bool: Tüm eşleştirmeler doğru mu?
        """
        if not isinstance(answer, dict) or not isinstance(correct, dict):
            return False
        
        # Tüm anahtarlar eşleşmeli
        if set(answer.keys()) != set(correct.keys()):
            return False
        
        # Her eşleştirme doğru olmalı
        for key, value in correct.items():
            if str(answer.get(key)) != str(value):
                return False
        
        return True
    
    def get_matching_score(self, answer) -> float:
        """
        Eşleştirme için kısmi puan hesapla.
        
        Args:
            answer: Kullanıcı cevabı {"0": "1", "1": "2", ...}
        
        Returns:
            float: 0.0 - 1.0 arası puan oranı
        """
        if self.question_type != self.QuestionType.MATCHING:
            return 1.0 if self.check_answer(answer) else 0.0
        
        correct = self.correct_answer
        
        if not isinstance(answer, dict) or not isinstance(correct, dict):
            return 0.0
        
        if not correct:
            return 0.0
        
        correct_count = 0
        total_count = len(correct)
        
        for key, value in correct.items():
            if str(answer.get(key)) == str(value):
                correct_count += 1
        
        return correct_count / total_count


class QuizAttempt(TenantAwareModel):
    """
    Quiz denemesi.
    
    Her kullanıcı quiz'e başladığında yeni bir attempt oluşturulur.
    """
    
    class Status(models.TextChoices):
        STARTED = 'started', _('Başladı')
        IN_PROGRESS = 'in_progress', _('Devam Ediyor')
        SUBMITTED = 'submitted', _('Gönderildi')
        GRADED = 'graded', _('Notlandırıldı')
        EXPIRED = 'expired', _('Süresi Doldu')
    
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name=_('Quiz'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name=_('Kullanıcı'),
    )
    
    # Video içi quiz için
    course = models.ForeignKey(
        'courses.Course',
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name=_('Kurs'),
        null=True,
        blank=True,
    )
    
    content = models.ForeignKey(
        'courses.CourseContent',
        on_delete=models.CASCADE,
        related_name='quiz_attempts',
        verbose_name=_('İçerik'),
        null=True,
        blank=True,
    )
    
    session = models.ForeignKey(
        'player.PlaybackSession',
        on_delete=models.SET_NULL,
        related_name='quiz_attempts',
        verbose_name=_('Oturum'),
        null=True,
        blank=True,
    )
    
    # Durum
    status = models.CharField(
        _('Durum'),
        max_length=20,
        choices=Status.choices,
        default=Status.STARTED,
    )
    
    # Puanlama
    score = models.DecimalField(
        _('Puan'),
        max_digits=6,
        decimal_places=2,
        default=0,
    )
    
    max_score = models.DecimalField(
        _('Maksimum Puan'),
        max_digits=6,
        decimal_places=2,
        default=0,
    )
    
    passed = models.BooleanField(
        _('Geçti'),
        default=False,
    )
    
    # Zamanlar
    started_at = models.DateTimeField(
        _('Başlangıç'),
        default=timezone.now,
    )
    
    submitted_at = models.DateTimeField(
        _('Gönderilme'),
        null=True,
        blank=True,
    )
    
    expires_at = models.DateTimeField(
        _('Süre Bitiş'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Quiz Denemesi')
        verbose_name_plural = _('Quiz Denemeleri')
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['tenant', 'quiz', 'user']),
            models.Index(fields=['tenant', 'user', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.quiz.title} ({self.score})"
    
    @property
    def score_percent(self) -> float:
        if self.max_score <= 0:
            return 0
        return float(self.score / self.max_score * 100)
    
    @property
    def is_expired(self) -> bool:
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def calculate_score(self):
        """Puanı hesapla."""
        total_score = 0
        max_score = 0
        
        for answer in self.answers.all():
            max_score += float(answer.question.points)
            if answer.is_correct:
                total_score += float(answer.points_awarded)
        
        self.score = total_score
        self.max_score = max_score
        self.passed = self.score_percent >= float(self.quiz.passing_score)
        self.save(update_fields=['score', 'max_score', 'passed', 'updated_at'])


class QuizAnswer(TenantAwareModel):
    """
    Quiz cevabı.
    
    Her attempt için her soru için bir cevap kaydı.
    """
    
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('Deneme'),
    )
    
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name=_('Soru'),
    )
    
    answer = models.JSONField(
        _('Cevap'),
        null=True,
        blank=True,
    )
    
    is_correct = models.BooleanField(
        _('Doğru'),
        null=True,
        blank=True,
    )
    
    points_awarded = models.DecimalField(
        _('Verilen Puan'),
        max_digits=5,
        decimal_places=2,
        default=0,
    )
    
    answered_at = models.DateTimeField(
        _('Cevaplanma'),
        null=True,
        blank=True,
    )
    
    class Meta:
        verbose_name = _('Quiz Cevabı')
        verbose_name_plural = _('Quiz Cevapları')
        ordering = ['question__order']
        constraints = [
            models.UniqueConstraint(
                fields=['attempt', 'question'],
                name='unique_attempt_question'
            )
        ]
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.attempt} - Q{self.question.order + 1}"
    
    def grade(self):
        """
        Cevabı notlandır.
        
        Eşleştirme sorularında kısmi puan verilebilir.
        Diğer soru türlerinde ya tam puan ya da sıfır.
        """
        if self.question.question_type == QuizQuestion.QuestionType.MATCHING:
            # Eşleştirme için kısmi puan
            score_ratio = self.question.get_matching_score(self.answer)
            self.points_awarded = float(self.question.points) * score_ratio
            self.is_correct = score_ratio == 1.0  # Tam doğru mu?
        else:
            # Diğer türler için tam/sıfır
            self.is_correct = self.question.check_answer(self.answer)
            self.points_awarded = self.question.points if self.is_correct else 0
        
        self.answered_at = timezone.now()
        self.save(update_fields=['is_correct', 'points_awarded', 'answered_at', 'updated_at'])

