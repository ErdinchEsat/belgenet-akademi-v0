"""
Quizzes Serializers
===================

Quiz API serializer'ları.
"""

from rest_framework import serializers

from .models import Quiz, QuizQuestion, QuizAttempt, QuizAnswer


class QuizQuestionSerializer(serializers.ModelSerializer):
    """
    Quiz sorusu serializer (öğrenci için - cevapsız).
    
    Eşleştirme soruları için options formatı:
    {
        "left": ["Başkent", "Dil", "Para Birimi"],
        "right": ["Ankara", "Türkçe", "Türk Lirası"]
    }
    
    Diğer sorular için options formatı:
    ["A seçeneği", "B seçeneği", "C seçeneği"]
    """
    
    class Meta:
        model = QuizQuestion
        fields = [
            'id',
            'question_type',
            'prompt',
            'options',
            'points',
            'order',
        ]


class QuizQuestionWithAnswerSerializer(serializers.ModelSerializer):
    """Quiz sorusu serializer (sonuç için - cevaplı)."""
    
    class Meta:
        model = QuizQuestion
        fields = [
            'id',
            'question_type',
            'prompt',
            'options',
            'correct_answer',
            'explanation',
            'points',
            'order',
        ]


class QuizSerializer(serializers.ModelSerializer):
    """Quiz serializer."""
    
    questions = QuizQuestionSerializer(many=True, read_only=True)
    question_count = serializers.IntegerField(read_only=True)
    total_points = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'description',
            'passing_score',
            'time_limit_minutes',
            'max_attempts',
            'shuffle_questions',
            'shuffle_options',
            'show_correct_answers',
            'question_count',
            'total_points',
            'questions',
        ]


class AttemptStartSerializer(serializers.Serializer):
    """
    Quiz başlatma request serializer.
    
    POST /api/v1/quizzes/{quizId}/attempts/
    """
    
    course_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    
    content_id = serializers.IntegerField(
        required=False,
        allow_null=True,
    )
    
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class AttemptResponseSerializer(serializers.ModelSerializer):
    """Quiz attempt response serializer."""
    
    score_percent = serializers.FloatField(read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id',
            'quiz',
            'status',
            'score',
            'max_score',
            'score_percent',
            'passed',
            'started_at',
            'submitted_at',
            'expires_at',
        ]


class AnswerSubmitSerializer(serializers.Serializer):
    """
    Tek cevap submit serializer.
    
    Cevap formatları:
    - mcq: "A" veya "B" (string)
    - multi: ["A", "B"] (list)
    - truefalse: true/false (boolean)
    - short: "cevap metni" (string)
    - matching: {"0": "2", "1": "0", "2": "1"} (dict - sol index -> sağ index)
    """
    
    question_id = serializers.UUIDField()
    answer = serializers.JSONField()


class QuizSubmitSerializer(serializers.Serializer):
    """
    Quiz submit request serializer.
    
    POST /api/v1/quizzes/{quizId}/attempts/{attemptId}/submit
    """
    
    answers = AnswerSubmitSerializer(many=True)


class QuizResultSerializer(serializers.Serializer):
    """
    Quiz sonuç serializer.
    
    Response 200:
    {
        "attempt_id": "uuid",
        "score": 80,
        "max_score": 100,
        "score_percent": 80.0,
        "passed": true,
        "answers": [...]
    }
    """
    
    attempt_id = serializers.UUIDField()
    score = serializers.FloatField()
    max_score = serializers.FloatField()
    score_percent = serializers.FloatField()
    passed = serializers.BooleanField()
    answers = serializers.ListField(child=serializers.DictField())


class QuizAnswerSerializer(serializers.ModelSerializer):
    """Quiz cevabı serializer."""
    
    question = QuizQuestionWithAnswerSerializer(read_only=True)
    
    class Meta:
        model = QuizAnswer
        fields = [
            'id',
            'question',
            'answer',
            'is_correct',
            'points_awarded',
            'answered_at',
        ]

