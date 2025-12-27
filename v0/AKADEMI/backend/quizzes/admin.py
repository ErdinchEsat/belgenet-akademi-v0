"""
Quizzes Admin
=============

Django admin panel konfigürasyonu.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Quiz, QuizQuestion, QuizAttempt, QuizAnswer


class QuizQuestionInline(admin.TabularInline):
    """Quiz soruları inline."""
    
    model = QuizQuestion
    extra = 0
    fields = ['order', 'question_type', 'prompt', 'options', 'correct_answer', 'points']
    readonly_fields = ['id']
    ordering = ['order']


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    """Quiz admin konfigürasyonu."""
    
    list_display = [
        'id',
        'title',
        'question_count',
        'passing_score',
        'time_limit_minutes',
        'is_blocking',
        'is_active',
    ]
    
    list_filter = [
        'is_active',
        'is_blocking',
        'tenant',
    ]
    
    search_fields = [
        'title',
        'description',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    inlines = [QuizQuestionInline]
    
    def question_count(self, obj):
        return obj.questions.count()
    question_count.short_description = 'Soru Sayısı'


@admin.register(QuizQuestion)
class QuizQuestionAdmin(admin.ModelAdmin):
    """
    Quiz sorusu admin konfigürasyonu.
    
    Eşleştirme Sorusu Formatı:
    -------------------------
    options: {"left": ["Sol 1", "Sol 2"], "right": ["Sağ A", "Sağ B"]}
    correct_answer: {"0": "1", "1": "0"}  (Sol 1 -> Sağ B, Sol 2 -> Sağ A)
    """
    
    list_display = [
        'id',
        'quiz_title',
        'question_type',
        'prompt_short',
        'points',
        'order',
    ]
    
    list_filter = [
        'question_type',
        'tenant',
    ]
    
    search_fields = [
        'prompt',
        'quiz__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        (None, {
            'fields': ('quiz', 'question_type', 'prompt', 'order', 'points')
        }),
        ('Seçenekler & Cevap', {
            'fields': ('options', 'correct_answer', 'explanation'),
            'description': '''
                <strong>Soru Türlerine Göre Format:</strong><br>
                <b>MCQ/Multi:</b> options: ["A", "B", "C"], correct_answer: "A" veya ["A", "B"]<br>
                <b>True/False:</b> options: [], correct_answer: true/false<br>
                <b>Short:</b> options: [], correct_answer: "cevap"<br>
                <b>Matching:</b> options: {"left": ["...", "..."], "right": ["...", "..."]}, 
                correct_answer: {"0": "1", "1": "0"} (sol index -> sağ index)
            '''
        }),
        ('Meta', {
            'fields': ('id', 'tenant', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def quiz_title(self, obj):
        return obj.quiz.title
    quiz_title.short_description = 'Quiz'
    
    def prompt_short(self, obj):
        return obj.prompt[:50] + '...' if len(obj.prompt) > 50 else obj.prompt
    prompt_short.short_description = 'Soru'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    """Quiz attempt admin konfigürasyonu."""
    
    list_display = [
        'id',
        'user_email',
        'quiz_title',
        'score_display',
        'status_badge',
        'started_at',
    ]
    
    list_filter = [
        'status',
        'passed',
        'tenant',
        'started_at',
    ]
    
    search_fields = [
        'user__email',
        'quiz__title',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'quiz',
        'user',
        'course',
        'content',
        'session',
        'status',
        'score',
        'max_score',
        'passed',
        'started_at',
        'submitted_at',
        'expires_at',
        'created_at',
        'updated_at',
    ]
    
    date_hierarchy = 'started_at'
    
    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'Kullanıcı'
    
    def quiz_title(self, obj):
        return obj.quiz.title
    quiz_title.short_description = 'Quiz'
    
    def score_display(self, obj):
        return f'{obj.score}/{obj.max_score} ({obj.score_percent:.0f}%)'
    score_display.short_description = 'Puan'
    
    def status_badge(self, obj):
        colors = {
            'started': 'blue',
            'in_progress': 'orange',
            'submitted': 'purple',
            'graded': 'green' if obj.passed else 'red',
            'expired': 'gray',
        }
        color = colors.get(obj.status, 'gray')
        icon = '✓' if obj.passed else '✗' if obj.status == 'graded' else '○'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, icon, obj.get_status_display()
        )
    status_badge.short_description = 'Durum'


@admin.register(QuizAnswer)
class QuizAnswerAdmin(admin.ModelAdmin):
    """Quiz cevabı admin konfigürasyonu."""
    
    list_display = [
        'id',
        'attempt_user',
        'question_short',
        'answer_display',
        'correct_badge',
        'points_awarded',
    ]
    
    list_filter = [
        'is_correct',
        'tenant',
    ]
    
    readonly_fields = [
        'id',
        'tenant',
        'attempt',
        'question',
        'answer',
        'is_correct',
        'points_awarded',
        'answered_at',
        'created_at',
        'updated_at',
    ]
    
    def attempt_user(self, obj):
        return obj.attempt.user.email
    attempt_user.short_description = 'Kullanıcı'
    
    def question_short(self, obj):
        return f"Q{obj.question.order + 1}"
    question_short.short_description = 'Soru'
    
    def answer_display(self, obj):
        return str(obj.answer)[:30]
    answer_display.short_description = 'Cevap'
    
    def correct_badge(self, obj):
        if obj.is_correct is None:
            return '-'
        if obj.is_correct:
            return format_html('<span style="color: green;">✓</span>')
        return format_html('<span style="color: red;">✗</span>')
    correct_badge.short_description = 'Doğru'

