"""
Student Serializers
==================

Öğrenci modülü serializer'ları.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import (
    Assignment,
    AssignmentSubmission,
    ClassEnrollment,
    ClassGroup,
    LiveSession,
    Message,
    Notification,
    SupportTicket,
)

User = get_user_model()


class InstructorSerializer(serializers.ModelSerializer):
    """Eğitmen bilgisi."""
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'avatar']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email

    def get_avatar(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            # Check for different possible avatar field names
            if hasattr(obj.profile, 'avatar_url') and obj.profile.avatar_url:
                return obj.profile.avatar_url
            if hasattr(obj.profile, 'avatar') and obj.profile.avatar:
                return obj.profile.avatar.url if hasattr(obj.profile.avatar, 'url') else str(obj.profile.avatar)
        return f"https://ui-avatars.com/api/?name={obj.first_name}+{obj.last_name}&background=random"


class CourseMinimalSerializer(serializers.Serializer):
    """Minimal kurs bilgisi."""
    id = serializers.IntegerField()
    title = serializers.CharField()


class ClassGroupListSerializer(serializers.ModelSerializer):
    """Sınıf listesi serializer."""
    course = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    nextLive = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()

    class Meta:
        model = ClassGroup
        fields = [
            'id', 'name', 'code', 'type', 'status', 'term',
            'course', 'teacher', 'avatar', 'nextLive', 'tasks',
        ]

    def get_course(self, obj):
        return obj.course.title

    def get_teacher(self, obj):
        instructor = obj.instructors.first()
        if instructor:
            return f"{instructor.first_name} {instructor.last_name}".strip()
        return ""

    def get_avatar(self, obj):
        instructor = obj.instructors.first()
        if instructor:
            return f"https://ui-avatars.com/api/?name={instructor.first_name}+{instructor.last_name}&background=random"
        return ""

    def get_nextLive(self, obj):
        from django.utils import timezone
        next_session = obj.live_sessions.filter(
            status__in=['SCHEDULED', 'LIVE'],
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at').first()
        
        if next_session:
            if next_session.status == 'LIVE':
                return "Şimdi Canlı"
            # Format date
            scheduled = next_session.scheduled_at
            today = timezone.now().date()
            if scheduled.date() == today:
                return f"Bugün {scheduled.strftime('%H:%M')}"
            elif (scheduled.date() - today).days == 1:
                return f"Yarın {scheduled.strftime('%H:%M')}"
            else:
                return scheduled.strftime('%d/%m %H:%M')
        return None

    def get_tasks(self, obj):
        from django.utils import timezone
        return obj.assignments.filter(
            status='PUBLISHED',
            due_date__gte=timezone.now()
        ).count()


class ClassGroupDetailSerializer(serializers.ModelSerializer):
    """Sınıf detay serializer."""
    course = CourseMinimalSerializer(read_only=True)
    instructors = InstructorSerializer(many=True, read_only=True)
    students = serializers.SerializerMethodField()
    workload = serializers.SerializerMethodField()
    nextLiveSession = serializers.SerializerMethodField()

    class Meta:
        model = ClassGroup
        fields = [
            'id', 'name', 'code', 'type', 'status', 'term', 'description',
            'course', 'instructors', 'students', 'capacity',
            'start_date', 'end_date', 'workload', 'nextLiveSession',
            'created_at', 'updated_at',
        ]

    def get_course(self, obj):
        return {'id': obj.course.id, 'title': obj.course.title}

    def get_students(self, obj):
        return {
            'total': obj.student_count,
            'passive': obj.passive_student_count,
        }

    def get_workload(self, obj):
        from django.utils import timezone
        pending_assignments = obj.assignments.filter(
            status='PUBLISHED',
            due_date__gte=timezone.now()
        ).count()
        return {
            'missingAssignments': pending_assignments,
            'toRead': 0,
            'pendingGrades': 0,
            'uncheckedQuiz': 0,
        }

    def get_nextLiveSession(self, obj):
        from django.utils import timezone
        next_session = obj.live_sessions.filter(
            status__in=['SCHEDULED', 'LIVE'],
            scheduled_at__gte=timezone.now()
        ).order_by('scheduled_at').first()
        
        if next_session:
            return {
                'at': next_session.scheduled_at.isoformat(),
                'title': next_session.title,
            }
        return None


class AssignmentListSerializer(serializers.ModelSerializer):
    """Ödev listesi serializer."""
    classId = serializers.CharField(source='class_group.id')
    className = serializers.CharField(source='class_group.name')
    dueDate = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ['id', 'title', 'classId', 'className', 'dueDate', 'status', 'description']

    def get_dueDate(self, obj):
        from django.utils import timezone
        due = obj.due_date
        today = timezone.now()
        
        if due.date() == today.date():
            return f"Bugün, {due.strftime('%H:%M')}"
        elif due.date() < today.date():
            return "Geçmiş"
        elif (due.date() - today.date()).days == 1:
            return f"Yarın, {due.strftime('%H:%M')}"
        else:
            return due.strftime('%d/%m, %H:%M')

    def get_status(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 'PENDING'
        
        submission = obj.submissions.filter(student=request.user).first()
        if not submission:
            from django.utils import timezone
            if obj.due_date < timezone.now():
                return 'LATE'
            return 'PENDING'
        return submission.status


class AssignmentDetailSerializer(serializers.ModelSerializer):
    """Ödev detay serializer."""
    classId = serializers.CharField(source='class_group.id')
    className = serializers.CharField(source='class_group.name')
    submission = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'description', 'classId', 'className',
            'due_date', 'status', 'max_score', 'attachments',
            'submission', 'created_at',
        ]

    def get_submission(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        submission = obj.submissions.filter(student=request.user).first()
        if submission:
            return AssignmentSubmissionSerializer(submission).data
        return None


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """Ödev teslimi serializer."""
    grade = serializers.IntegerField(source='score', read_only=True)

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'status', 'content', 'attachments',
            'grade', 'feedback', 'submitted_at', 'graded_at',
        ]


class AssignmentSubmitSerializer(serializers.Serializer):
    """Ödev teslim etme."""
    content = serializers.CharField(required=False, allow_blank=True)
    attachments = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        default=list,
    )


class LiveSessionListSerializer(serializers.ModelSerializer):
    """Canlı ders listesi serializer."""
    classId = serializers.CharField(source='class_group.id')
    className = serializers.CharField(source='class_group.name')
    instructor = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()

    class Meta:
        model = LiveSession
        fields = [
            'id', 'title', 'classId', 'className',
            'instructor', 'date', 'time', 'status',
            'duration_minutes', 'meeting_url',
        ]

    def get_instructor(self, obj):
        return f"{obj.instructor.first_name} {obj.instructor.last_name}".strip()

    def get_date(self, obj):
        from django.utils import timezone
        scheduled = obj.scheduled_at
        today = timezone.now().date()
        
        if scheduled.date() == today:
            return "Bugün"
        elif (scheduled.date() - today).days == 1:
            return "Yarın"
        elif scheduled.date() < today:
            return "Geçmiş"
        else:
            return scheduled.strftime('%d/%m/%Y')

    def get_time(self, obj):
        if obj.status == 'COMPLETED':
            return "-"
        return obj.scheduled_at.strftime('%H:%M')


class NotificationSerializer(serializers.ModelSerializer):
    """Bildirim serializer."""
    time = serializers.SerializerMethodField()
    isRead = serializers.BooleanField(source='is_read')

    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'type', 'source', 'action_url', 'isRead', 'time']

    def get_time(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(obj.created_at, timezone.now()) + " önce"


class MessageSerializer(serializers.ModelSerializer):
    """Mesaj serializer."""
    sender = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    time = serializers.SerializerMethodField()
    unread = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'sender', 'role', 'preview', 'time', 'unread', 'content', 'subject']

    def get_sender(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip()

    def get_role(self, obj):
        role_map = {
            'INSTRUCTOR': 'Eğitmen',
            'ADMIN': 'Admin',
            'TENANT_ADMIN': 'Yönetici',
            'STUDENT': 'Öğrenci',
        }
        return role_map.get(obj.sender.role, 'Kullanıcı')

    def get_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content

    def get_time(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        diff = timezone.now() - obj.created_at
        if diff.days == 0:
            return obj.created_at.strftime('%H:%M')
        elif diff.days == 1:
            return "Dün"
        else:
            return obj.created_at.strftime('%d/%m')

    def get_unread(self, obj):
        return not obj.is_read


class SupportTicketSerializer(serializers.ModelSerializer):
    """Destek talebi serializer."""
    date = serializers.SerializerMethodField()

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'description', 'category', 'status',
            'response', 'date', 'created_at',
        ]

    def get_date(self, obj):
        from django.utils import timezone
        from django.utils.timesince import timesince
        
        diff = timezone.now() - obj.created_at
        if diff.days == 0:
            return "Bugün"
        elif diff.days == 1:
            return "Dün"
        elif diff.days < 7:
            return f"{diff.days} gün önce"
        else:
            return obj.created_at.strftime('%d/%m/%Y')


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """Destek talebi oluşturma."""
    
    class Meta:
        model = SupportTicket
        fields = ['subject', 'description', 'category']

