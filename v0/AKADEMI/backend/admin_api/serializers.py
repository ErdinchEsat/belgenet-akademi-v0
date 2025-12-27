"""
Admin API Serializers
=====================

Serializers for admin dashboard, user management, and analytics.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


# =============================================================================
# TENANT DASHBOARD SERIALIZERS
# =============================================================================

class TenantDashboardKPIsSerializer(serializers.Serializer):
    """KPI verilerini serialize eder."""
    activeCourses = serializers.IntegerField()
    activeClasses = serializers.IntegerField()
    activeInstructors = serializers.IntegerField()
    activeStudents = serializers.IntegerField()
    todayLiveSessions = serializers.IntegerField()


class TodayOperationsPrimarySerializer(serializers.Serializer):
    """Bugünkü operasyonların ana verileri."""
    examsStarting = serializers.IntegerField()
    assignmentsClosing = serializers.IntegerField()
    liveSessionsCount = serializers.IntegerField()


class TodayOperationsExceptionsSerializer(serializers.Serializer):
    """Bugünkü operasyonların istisnaları."""
    attendanceMissing = serializers.IntegerField()
    pendingSchedules = serializers.IntegerField()
    instructorRejections = serializers.IntegerField()


class TodayOperationsSerializer(serializers.Serializer):
    """Bugünkü operasyonlar."""
    primary = TodayOperationsPrimarySerializer()
    exceptions = TodayOperationsExceptionsSerializer()


class HealthMetricItemSerializer(serializers.Serializer):
    """Tek bir sağlık metriği."""
    value = serializers.IntegerField()
    trend = serializers.FloatField()
    trendDir = serializers.ChoiceField(choices=['up', 'down'])


class HealthMetricsSerializer(serializers.Serializer):
    """Kurum sağlık metrikleri."""
    avgLiveAttendance = HealthMetricItemSerializer()
    avgVideoCompletion = HealthMetricItemSerializer()
    missingHomeworkRate = HealthMetricItemSerializer()
    riskyStudents = HealthMetricItemSerializer()


class PlanningDataSerializer(serializers.Serializer):
    """Planlama verileri."""
    pendingApprovals = serializers.IntegerField()
    conflicts = serializers.IntegerField()
    changesToday = serializers.IntegerField()


class ProblemAreaSerializer(serializers.Serializer):
    """Problem alanı."""
    id = serializers.IntegerField()
    type = serializers.CharField()
    label = serializers.CharField()
    value = serializers.CharField()
    context = serializers.CharField()
    severity = serializers.ChoiceField(choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'])


class RecentActivitySerializer(serializers.Serializer):
    """Son aktivite."""
    id = serializers.IntegerField()
    type = serializers.CharField()
    user = serializers.CharField()
    action = serializers.CharField()
    target = serializers.CharField()
    timestamp = serializers.DateTimeField()


class QuickActionSerializer(serializers.Serializer):
    """Hızlı aksiyon."""
    id = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()
    count = serializers.IntegerField()
    actionUrl = serializers.CharField()
    color = serializers.CharField()


class TenantDashboardSerializer(serializers.Serializer):
    """
    Tenant Manager Dashboard için tam veri serializeri.
    
    İçerir:
    - kpis: Ana KPI verileri
    - todayOps: Bugünkü operasyonlar
    - healthMetrics: Kurum sağlık metrikleri
    - planningData: Planlama verileri
    - problemAreas: Problem alanları listesi
    - recentActivities: Son aktiviteler (opsiyonel)
    - quickActions: Hızlı aksiyonlar (opsiyonel)
    """
    kpis = TenantDashboardKPIsSerializer()
    todayOps = TodayOperationsSerializer()
    healthMetrics = HealthMetricsSerializer()
    planningData = PlanningDataSerializer()
    problemAreas = ProblemAreaSerializer(many=True)
    recentActivities = RecentActivitySerializer(many=True, required=False)
    quickActions = QuickActionSerializer(many=True, required=False)


# =============================================================================
# ADMIN USER MANAGEMENT SERIALIZERS
# =============================================================================

class AdminUserSerializer(serializers.ModelSerializer):
    """
    Admin için genişletilmiş kullanıcı serializeri.
    """
    name = serializers.CharField(source='full_name', read_only=True)
    tenantId = serializers.CharField(source='tenant_id', read_only=True)
    tenantName = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    lastActive = serializers.SerializerMethodField()
    enrollmentsCount = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'first_name',
            'last_name',
            'role',
            'avatar',
            'title',
            'tenantId',
            'tenantName',
            'status',
            'is_active',
            'points',
            'streak',
            'lastActive',
            'enrollmentsCount',
            'date_joined',
            'last_login',
            'phone',
            'bio',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'points', 'streak']

    def get_avatar(self, obj) -> str:
        return obj.get_avatar_url()
    
    def get_tenantName(self, obj) -> str:
        return obj.tenant.name if obj.tenant else None
    
    def get_status(self, obj) -> str:
        if not obj.is_active:
            return 'Suspended'
        if obj.last_login is None:
            return 'Pending'
        return 'Active'
    
    def get_lastActive(self, obj) -> str:
        if obj.last_login:
            return obj.last_login.strftime('%d.%m.%Y %H:%M')
        return '-'
    
    def get_enrollmentsCount(self, obj) -> int:
        if hasattr(obj, 'enrollments'):
            return obj.enrollments.count()
        return 0


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    Admin tarafından kullanıcı oluşturma serializeri.
    """
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    sendInvite = serializers.BooleanField(write_only=True, default=True)
    
    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'first_name',
            'last_name',
            'role',
            'tenant',
            'title',
            'phone',
            'sendInvite',
        ]
    
    def create(self, validated_data):
        send_invite = validated_data.pop('sendInvite', True)
        password = validated_data.pop('password', None)
        
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)
        else:
            # Geçici rastgele şifre oluştur
            import secrets
            temp_password = secrets.token_urlsafe(12)
            user.set_password(temp_password)
        
        user.save()
        
        # TODO: send_invite True ise davet e-postası gönder
        
        return user


class AdminUserUpdateSerializer(serializers.ModelSerializer):
    """
    Admin tarafından kullanıcı güncelleme serializeri.
    """
    class Meta:
        model = User
        fields = [
            'email',
            'first_name',
            'last_name',
            'role',
            'tenant',
            'title',
            'phone',
            'bio',
            'avatar',
            'is_active',
            'notify_email',
            'notify_push',
        ]
    
    def update(self, instance, validated_data):
        # Rol değişikliği için özel kontrol
        new_role = validated_data.get('role')
        if new_role and new_role == User.Role.SUPER_ADMIN:
            request = self.context.get('request')
            if request and request.user.role != User.Role.SUPER_ADMIN:
                raise serializers.ValidationError({
                    'role': 'Super Admin rolü atama yetkiniz yok.'
                })
        
        return super().update(instance, validated_data)


class UserStatsSerializer(serializers.Serializer):
    """
    Kullanıcı istatistikleri serializeri.
    """
    totalUsers = serializers.IntegerField()
    activeUsers = serializers.IntegerField()
    pendingUsers = serializers.IntegerField()
    suspendedUsers = serializers.IntegerField()
    studentCount = serializers.IntegerField()
    instructorCount = serializers.IntegerField()
    adminCount = serializers.IntegerField()
    newUsersThisMonth = serializers.IntegerField()
    newUsersLastMonth = serializers.IntegerField()
    growthPercent = serializers.FloatField()


class BulkUserImportSerializer(serializers.Serializer):
    """
    Toplu kullanıcı import serializeri.
    """
    file = serializers.FileField()
    defaultRole = serializers.ChoiceField(
        choices=User.Role.choices,
        default=User.Role.STUDENT,
    )
    sendInvites = serializers.BooleanField(default=True)
    skipExisting = serializers.BooleanField(default=True)


class BulkUserImportResultSerializer(serializers.Serializer):
    """
    Toplu import sonuç serializeri.
    """
    total = serializers.IntegerField()
    created = serializers.IntegerField()
    skipped = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.DictField())


class PasswordResetSerializer(serializers.Serializer):
    """
    Şifre sıfırlama serializeri.
    """
    sendEmail = serializers.BooleanField(default=True)
    newPassword = serializers.CharField(required=False, validators=[validate_password])


# =============================================================================
# ADMIN COURSE MANAGEMENT SERIALIZERS
# =============================================================================

class AdminCourseSerializer(serializers.Serializer):
    """
    Admin için genişletilmiş kurs serializeri.
    """
    id = serializers.IntegerField()
    title = serializers.CharField()
    slug = serializers.CharField()
    description = serializers.CharField()
    shortDescription = serializers.CharField(source='short_description')
    coverUrl = serializers.SerializerMethodField()
    category = serializers.CharField()
    language = serializers.CharField()
    level = serializers.CharField()
    tags = serializers.JSONField()
    status = serializers.CharField()
    isPublished = serializers.BooleanField(source='is_published')
    
    # Pricing
    isFree = serializers.BooleanField(source='is_free')
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    
    # Stats
    enrolledCount = serializers.IntegerField(source='enrolled_count')
    rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    ratingCount = serializers.IntegerField(source='rating_count')
    totalDurationMinutes = serializers.IntegerField(source='total_duration_minutes')
    
    # Instructors
    instructors = serializers.SerializerMethodField()
    
    # Tenant
    tenantId = serializers.SerializerMethodField()
    tenantName = serializers.SerializerMethodField()
    
    # Workflow
    teacherSubmitNote = serializers.CharField(source='teacher_submit_note', allow_blank=True)
    adminRevisionNote = serializers.CharField(source='admin_revision_note', allow_blank=True)
    
    # Dates
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    publishAt = serializers.DateTimeField(source='publish_at', allow_null=True)
    
    def get_coverUrl(self, obj):
        return obj.cover_url_display
    
    def get_instructors(self, obj):
        return [
            {
                'id': str(inst.id),
                'name': inst.full_name,
                'email': inst.email,
                'avatar': inst.get_avatar_url(),
            }
            for inst in obj.instructors.all()
        ]
    
    def get_tenantId(self, obj):
        return str(obj.tenant.id) if obj.tenant else None
    
    def get_tenantName(self, obj):
        return obj.tenant.name if obj.tenant else None


class AdminCourseUpdateSerializer(serializers.Serializer):
    """
    Admin tarafından kurs güncelleme serializeri.
    """
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    shortDescription = serializers.CharField(required=False, source='short_description')
    coverUrl = serializers.URLField(required=False, source='cover_url')
    category = serializers.CharField(required=False)
    level = serializers.CharField(required=False)
    tags = serializers.JSONField(required=False)
    isFree = serializers.BooleanField(required=False, source='is_free')
    price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    currency = serializers.CharField(required=False)
    certificateEnabled = serializers.BooleanField(required=False, source='certificate_enabled')
    completionPercent = serializers.IntegerField(required=False, source='completion_percent')


class CourseStatsSerializer(serializers.Serializer):
    """
    Kurs istatistikleri serializeri.
    """
    totalCourses = serializers.IntegerField()
    publishedCourses = serializers.IntegerField()
    pendingCourses = serializers.IntegerField()
    revisionCourses = serializers.IntegerField()
    draftCourses = serializers.IntegerField()
    archivedCourses = serializers.IntegerField()
    totalEnrollments = serializers.IntegerField()
    averageRating = serializers.FloatField()
    totalRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    categoryCounts = serializers.DictField()


class CourseCategorySerializer(serializers.Serializer):
    """
    Kurs kategorisi serializeri.
    """
    id = serializers.CharField()
    name = serializers.CharField()
    slug = serializers.CharField()
    courseCount = serializers.IntegerField()
    color = serializers.CharField(required=False)
    icon = serializers.CharField(required=False)


class CourseApprovalSerializer(serializers.Serializer):
    """
    Kurs onay işlemi serializeri.
    """
    note = serializers.CharField(required=False, allow_blank=True)
    publishAt = serializers.DateTimeField(required=False)


class CourseBulkActionSerializer(serializers.Serializer):
    """
    Toplu kurs işlemleri serializeri.
    """
    courseIds = serializers.ListField(child=serializers.IntegerField())
    action = serializers.ChoiceField(choices=['approve', 'archive', 'unpublish', 'delete'])
    note = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# ADMIN CLASS GROUP SERIALIZERS
# =============================================================================

class AdminClassGroupSerializer(serializers.Serializer):
    """
    Admin için genişletilmiş sınıf serializeri.
    """
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()
    type = serializers.CharField()
    status = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    term = serializers.CharField(allow_blank=True)
    capacity = serializers.IntegerField()
    
    # İlişkiler
    course = serializers.SerializerMethodField()
    instructors = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    
    # Tenant
    tenantId = serializers.SerializerMethodField()
    tenantName = serializers.SerializerMethodField()
    
    # İstatistikler
    health = serializers.SerializerMethodField()
    workload = serializers.SerializerMethodField()
    approvals = serializers.SerializerMethodField()
    nextLiveSession = serializers.SerializerMethodField()
    
    # Tarihler
    startDate = serializers.DateField(source='start_date', allow_null=True)
    endDate = serializers.DateField(source='end_date', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    
    def get_course(self, obj):
        return {
            'id': str(obj.course.id),
            'title': obj.course.title,
            'slug': obj.course.slug,
        } if obj.course else None
    
    def get_instructors(self, obj):
        return [
            {
                'id': str(inst.id),
                'name': inst.full_name,
                'email': inst.email,
                'avatarUrl': inst.get_avatar_url(),
            }
            for inst in obj.instructors.all()
        ]
    
    def get_students(self, obj):
        total = obj.class_enrollments.count()
        active = obj.class_enrollments.filter(status='ACTIVE').count()
        passive = obj.class_enrollments.filter(status='PASSIVE').count()
        return {
            'total': total,
            'active': active,
            'passive': passive,
        }
    
    def get_tenantId(self, obj):
        return str(obj.tenant.id) if obj.tenant else None
    
    def get_tenantName(self, obj):
        return obj.tenant.name if obj.tenant else None
    
    def get_health(self, obj):
        # Sağlık durumu hesaplama
        students = obj.class_enrollments.all()
        if not students.exists():
            return 'HEALTHY'
        
        passive_ratio = obj.passive_student_count / max(obj.student_count + obj.passive_student_count, 1)
        
        if passive_ratio > 0.2:
            return 'INTERVENTION'
        elif passive_ratio > 0.1:
            return 'ATTENTION'
        return 'HEALTHY'
    
    def get_workload(self, obj):
        from backend.student.models import Assignment, AssignmentSubmission
        
        # Eksik ödevler
        open_assignments = Assignment.objects.filter(
            class_group=obj,
            status='PUBLISHED'
        )
        missing = 0
        for assignment in open_assignments:
            submitted = AssignmentSubmission.objects.filter(
                assignment=assignment,
                status__in=['SUBMITTED', 'GRADED']
            ).count()
            total = obj.student_count
            missing += max(0, total - submitted)
        
        # Notlandırılacak
        to_grade = AssignmentSubmission.objects.filter(
            assignment__class_group=obj,
            status='SUBMITTED'
        ).count()
        
        return {
            'missingAssignments': missing,
            'toRead': to_grade,
            'pendingGrades': to_grade,
            'uncheckedQuiz': 0,  # Quiz modeli yok
        }
    
    def get_approvals(self, obj):
        from backend.student.models import LiveSession, Assignment
        
        # Bekleyen canlı dersler (planlanmış ama onaylanmamış)
        pending_live = LiveSession.objects.filter(
            class_group=obj,
            status='SCHEDULED'
        ).count()
        
        # Bekleyen ödevler
        pending_assignments = Assignment.objects.filter(
            class_group=obj,
            status='DRAFT'
        ).count()
        
        return {
            'live': pending_live,
            'assignment': pending_assignments,
            'exam': 0,
            'quiz': 0,
        }
    
    def get_nextLiveSession(self, obj):
        from backend.student.models import LiveSession
        from django.utils import timezone
        
        next_session = LiveSession.objects.filter(
            class_group=obj,
            scheduled_at__gt=timezone.now(),
            status__in=['SCHEDULED', 'LIVE']
        ).order_by('scheduled_at').first()
        
        if next_session:
            return {
                'at': next_session.scheduled_at.isoformat(),
                'title': next_session.title,
            }
        return None


class AdminClassGroupCreateSerializer(serializers.Serializer):
    """
    Admin tarafından sınıf oluşturma serializeri.
    """
    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=['ACADEMIC', 'VOCATIONAL'], default='ACADEMIC')
    status = serializers.ChoiceField(choices=['ACTIVE', 'COMPLETED', 'ARCHIVED'], default='ACTIVE')
    description = serializers.CharField(required=False, allow_blank=True)
    term = serializers.CharField(max_length=50, required=False, allow_blank=True)
    capacity = serializers.IntegerField(required=False, default=50)
    courseId = serializers.IntegerField()
    instructorIds = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    startDate = serializers.DateField(required=False, allow_null=True)
    endDate = serializers.DateField(required=False, allow_null=True)


class AdminClassGroupUpdateSerializer(serializers.Serializer):
    """
    Admin tarafından sınıf güncelleme serializeri.
    """
    name = serializers.CharField(max_length=100, required=False)
    code = serializers.CharField(max_length=20, required=False)
    type = serializers.ChoiceField(choices=['ACADEMIC', 'VOCATIONAL'], required=False)
    status = serializers.ChoiceField(choices=['ACTIVE', 'COMPLETED', 'ARCHIVED'], required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    term = serializers.CharField(max_length=50, required=False)
    capacity = serializers.IntegerField(required=False)
    courseId = serializers.IntegerField(required=False)
    startDate = serializers.DateField(required=False, allow_null=True)
    endDate = serializers.DateField(required=False, allow_null=True)


class ClassGroupStatsSerializer(serializers.Serializer):
    """
    Sınıf istatistikleri serializeri.
    """
    totalClasses = serializers.IntegerField()
    activeClasses = serializers.IntegerField()
    completedClasses = serializers.IntegerField()
    archivedClasses = serializers.IntegerField()
    totalStudents = serializers.IntegerField()
    activeStudents = serializers.IntegerField()
    totalInstructors = serializers.IntegerField()
    healthyClasses = serializers.IntegerField()
    attentionClasses = serializers.IntegerField()
    interventionClasses = serializers.IntegerField()


class StudentAssignSerializer(serializers.Serializer):
    """
    Öğrenci atama serializeri.
    """
    studentIds = serializers.ListField(child=serializers.CharField())
    action = serializers.ChoiceField(choices=['add', 'remove'], default='add')


class InstructorAssignSerializer(serializers.Serializer):
    """
    Eğitmen atama serializeri.
    """
    instructorIds = serializers.ListField(child=serializers.CharField())
    action = serializers.ChoiceField(choices=['add', 'remove', 'replace'], default='add')


# =============================================================================
# OPS INBOX SERIALIZERS
# =============================================================================

class OpsInboxItemSerializer(serializers.Serializer):
    """
    Operasyon kutusu öğesi serializeri.
    """
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=['ASSIGNMENT', 'QUIZ', 'EXAM', 'LIVE_SESSION', 'COURSE'])
    title = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    
    # Gönderen
    submittedBy = serializers.SerializerMethodField()
    
    # Bağlam
    courseName = serializers.CharField()
    className = serializers.CharField()
    courseId = serializers.CharField(required=False)
    classId = serializers.CharField(required=False)
    
    # Tarihler
    submittedAt = serializers.DateTimeField()
    dueDate = serializers.DateTimeField(required=False, allow_null=True)
    slaDeadline = serializers.DateTimeField()
    
    # Durum
    status = serializers.ChoiceField(choices=['PENDING_APPROVAL', 'SLA_BREACHED', 'FLAGGED', 'RETURNED'])
    priority = serializers.ChoiceField(choices=['LOW', 'NORMAL', 'HIGH', 'URGENT'], default='NORMAL')
    
    # Uyarılar
    flags = serializers.ListField(child=serializers.CharField(), required=False)
    
    def get_submittedBy(self, obj):
        # obj bir dict olacak
        return obj.get('submittedBy', {})


class OpsInboxStatsSerializer(serializers.Serializer):
    """
    Ops Inbox istatistikleri serializeri.
    """
    totalPending = serializers.IntegerField()
    slaBreached = serializers.IntegerField()
    flagged = serializers.IntegerField()
    assignments = serializers.IntegerField()
    liveSessions = serializers.IntegerField()
    courses = serializers.IntegerField()
    todayDue = serializers.IntegerField()


class OpsActionSerializer(serializers.Serializer):
    """
    Ops aksiyon serializeri.
    """
    note = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class OpsBulkActionSerializer(serializers.Serializer):
    """
    Toplu ops aksiyon serializeri.
    """
    ids = serializers.ListField(child=serializers.CharField())
    action = serializers.ChoiceField(choices=['approve', 'reject', 'revision'])
    note = serializers.CharField(required=False, allow_blank=True)


# =============================================================================
# REPORTS SERIALIZERS
# =============================================================================

class CourseMetricSerializer(serializers.Serializer):
    """Kurs başarı metrikleri."""
    name = serializers.CharField()
    completion = serializers.FloatField()
    avgScore = serializers.FloatField()
    engagement = serializers.FloatField()
    enrollments = serializers.IntegerField(required=False)
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class InstructorPerformanceSerializer(serializers.Serializer):
    """Eğitmen performans metrikleri."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField()
    rating = serializers.FloatField()
    retention = serializers.FloatField()
    students = serializers.IntegerField()
    courses = serializers.IntegerField(required=False)
    liveSessions = serializers.IntegerField(required=False)
    status = serializers.ChoiceField(choices=['TOP_RATED', 'GOOD', 'NEEDS_IMPROVEMENT'])


class FailureReasonSerializer(serializers.Serializer):
    """Başarısızlık nedenleri."""
    reason = serializers.CharField()
    count = serializers.IntegerField()
    fill = serializers.CharField()
    percentage = serializers.FloatField(required=False)


class AIInsightSerializer(serializers.Serializer):
    """Yapay zeka içgörüleri."""
    id = serializers.IntegerField()
    type = serializers.ChoiceField(choices=['CRITICAL', 'WARNING', 'SUCCESS', 'INFO'])
    title = serializers.CharField()
    desc = serializers.CharField()
    action = serializers.CharField()
    relatedId = serializers.CharField(required=False, allow_null=True)
    relatedType = serializers.CharField(required=False, allow_null=True)


class GeneralStatsSerializer(serializers.Serializer):
    """Genel istatistikler."""
    overallSuccess = serializers.FloatField()
    completedLessons = serializers.IntegerField()
    riskyStudents = serializers.IntegerField()
    avgInstructorScore = serializers.FloatField()
    totalStudents = serializers.IntegerField(required=False)
    totalCourses = serializers.IntegerField(required=False)
    totalRevenue = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    avgCompletionRate = serializers.FloatField(required=False)


class ReportsDataSerializer(serializers.Serializer):
    """Raporlar ana serializeri."""
    courseMetrics = CourseMetricSerializer(many=True)
    instructorPerformance = InstructorPerformanceSerializer(many=True)
    failureReasons = FailureReasonSerializer(many=True)
    aiInsights = AIInsightSerializer(many=True)
    generalStats = GeneralStatsSerializer()


class UserActivityReportSerializer(serializers.Serializer):
    """Kullanıcı aktivite raporu."""
    date = serializers.DateField()
    activeUsers = serializers.IntegerField()
    newRegistrations = serializers.IntegerField()
    loginCount = serializers.IntegerField()
    courseViews = serializers.IntegerField()
    lessonCompletions = serializers.IntegerField()
    assignmentSubmissions = serializers.IntegerField()


class CoursePerformanceReportSerializer(serializers.Serializer):
    """Kurs performans raporu."""
    courseId = serializers.IntegerField()
    courseName = serializers.CharField()
    category = serializers.CharField(required=False)
    enrollments = serializers.IntegerField()
    completions = serializers.IntegerField()
    completionRate = serializers.FloatField()
    avgScore = serializers.FloatField()
    avgTimeSpent = serializers.IntegerField()  # dakika
    rating = serializers.FloatField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    dropoffRate = serializers.FloatField()


class RevenueReportSerializer(serializers.Serializer):
    """Gelir raporu."""
    date = serializers.DateField()
    courseRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    subscriptionRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    totalRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    refunds = serializers.DecimalField(max_digits=12, decimal_places=2)
    netRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class ReportFilterSerializer(serializers.Serializer):
    """Rapor filtre parametreleri."""
    startDate = serializers.DateField(required=False)
    endDate = serializers.DateField(required=False)
    courseId = serializers.IntegerField(required=False)
    instructorId = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    groupBy = serializers.ChoiceField(choices=['day', 'week', 'month'], default='day', required=False)


class ExportRequestSerializer(serializers.Serializer):
    """Export talep serializeri."""
    reportType = serializers.ChoiceField(choices=['user_activity', 'course_performance', 'revenue', 'instructor', 'full'])
    format = serializers.ChoiceField(choices=['pdf', 'excel', 'csv'])
    startDate = serializers.DateField(required=False)
    endDate = serializers.DateField(required=False)
    filters = serializers.DictField(required=False)


# =============================================================================
# ROLES & PERMISSIONS SERIALIZERS
# =============================================================================

class PermissionSerializer(serializers.Serializer):
    """Tekil izin serializeri."""
    id = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    dependencies = serializers.ListField(child=serializers.CharField(), required=False)


class PermissionGroupSerializer(serializers.Serializer):
    """İzin grubu serializeri."""
    id = serializers.CharField()
    label = serializers.CharField()
    icon = serializers.CharField()
    permissions = PermissionSerializer(many=True)


class RoleSerializer(serializers.Serializer):
    """Rol serializeri."""
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=['SYSTEM', 'CUSTOM'])
    userCount = serializers.IntegerField(read_only=True)
    permissions = serializers.ListField(child=serializers.CharField())
    hiddenSidebarModules = serializers.ListField(child=serializers.CharField(), required=False)
    baseRole = serializers.ChoiceField(choices=['INSTRUCTOR', 'STUDENT', 'NONE'], required=False, allow_null=True)


class RoleCreateSerializer(serializers.Serializer):
    """Rol oluşturma serializeri."""
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    baseRole = serializers.ChoiceField(choices=['INSTRUCTOR', 'STUDENT', 'NONE'], required=False)
    permissions = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    hiddenSidebarModules = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class RoleUpdateSerializer(serializers.Serializer):
    """Rol güncelleme serializeri."""
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    permissions = serializers.ListField(child=serializers.CharField(), required=False)
    hiddenSidebarModules = serializers.ListField(child=serializers.CharField(), required=False)


class RoleAssignSerializer(serializers.Serializer):
    """Kullanıcılara rol atama serializeri."""
    userIds = serializers.ListField(child=serializers.CharField())
    roleId = serializers.CharField()


# =============================================================================
# TENANT CONFIG SERIALIZERS (Super Admin)
# =============================================================================

class TenantFeaturesSerializer(serializers.Serializer):
    """Tenant özellikleri serializeri."""
    canUploadVideo = serializers.BooleanField(default=True)
    canUploadDocs = serializers.BooleanField(default=True)
    moduleQuiz = serializers.BooleanField(default=True)
    moduleExam = serializers.BooleanField(default=True)
    moduleAssignment = serializers.BooleanField(default=True)
    moduleLiveClass = serializers.BooleanField(default=False)


class TenantLimitsSerializer(serializers.Serializer):
    """Tenant limit serializeri."""
    totalStorage = serializers.IntegerField(default=10)  # GB
    maxVideoFileSize = serializers.IntegerField(default=1024)  # MB
    maxDocFileSize = serializers.IntegerField(default=5)  # MB
    maxCourses = serializers.IntegerField(default=20)
    maxLiveSessions = serializers.IntegerField(default=2)


class TenantUsageSerializer(serializers.Serializer):
    """Tenant kullanım serializeri."""
    usedVideo = serializers.FloatField(default=0)
    usedDocs = serializers.FloatField(default=0)


class TenantAdminSerializer(serializers.Serializer):
    """Tenant admin serializeri."""
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(required=False, allow_null=True)
    currentRole = serializers.CharField(required=False)


class TenantConfigSerializer(serializers.Serializer):
    """Tenant konfigürasyon serializeri."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=200)
    slug = serializers.CharField(max_length=100)
    type = serializers.CharField(max_length=50)
    color = serializers.CharField(max_length=20, default='blue')
    logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    users = serializers.IntegerField(read_only=True)
    status = serializers.ChoiceField(choices=['active', 'suspended', 'pending'], default='active')
    features = TenantFeaturesSerializer()
    limits = TenantLimitsSerializer()
    usage = TenantUsageSerializer(read_only=True)
    admin = TenantAdminSerializer(required=False, allow_null=True)


class TenantCreateSerializer(serializers.Serializer):
    """Tenant oluşturma serializeri."""
    name = serializers.CharField(max_length=200)
    slug = serializers.CharField(max_length=100)
    type = serializers.CharField(max_length=50, default='Kurumsal')
    color = serializers.CharField(max_length=20, default='blue')
    logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    features = TenantFeaturesSerializer(required=False)
    limits = TenantLimitsSerializer(required=False)
    adminId = serializers.CharField(required=False, allow_null=True)
    newAdmin = serializers.DictField(required=False, allow_null=True)


class TenantUpdateSerializer(serializers.Serializer):
    """Tenant güncelleme serializeri."""
    name = serializers.CharField(max_length=200, required=False)
    slug = serializers.CharField(max_length=100, required=False)
    type = serializers.CharField(max_length=50, required=False)
    color = serializers.CharField(max_length=20, required=False)
    logo = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    status = serializers.ChoiceField(choices=['active', 'suspended', 'pending'], required=False)
    features = TenantFeaturesSerializer(required=False)
    limits = TenantLimitsSerializer(required=False)
    adminId = serializers.CharField(required=False, allow_null=True)


# =============================================================================
# SYSTEM STATS SERIALIZERS (Super Admin)
# =============================================================================

class TenantStorageDataSerializer(serializers.Serializer):
    """Tenant depolama verileri."""
    name = serializers.CharField()
    video = serializers.FloatField()
    docs = serializers.FloatField()
    total = serializers.FloatField()
    color = serializers.CharField()


class SystemLoadDataSerializer(serializers.Serializer):
    """Sistem yük verileri."""
    time = serializers.CharField()
    cpu = serializers.IntegerField()
    ram = serializers.IntegerField()


class SystemStatsSerializer(serializers.Serializer):
    """Sistem istatistikleri serializeri."""
    totalDiskCapacity = serializers.IntegerField()
    totalUsed = serializers.IntegerField()
    tenantStorageData = TenantStorageDataSerializer(many=True)
    systemLoadData = SystemLoadDataSerializer(many=True)
    servicesStatus = serializers.ChoiceField(choices=['operational', 'degraded', 'down'])
    totalTenants = serializers.IntegerField()
    totalUsers = serializers.IntegerField()
    totalCourses = serializers.IntegerField()
    activeUsers = serializers.IntegerField()


# =============================================================================
# FINANCE SERIALIZERS (Super Admin)
# =============================================================================

class AcademyFinanceStatsSerializer(serializers.Serializer):
    """Akademi finansal istatistikleri."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    logo = serializers.CharField(required=False, allow_null=True)
    totalRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthlyRevenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    studentCount = serializers.IntegerField()
    courseCount = serializers.IntegerField()
    avgCoursePrice = serializers.DecimalField(max_digits=10, decimal_places=2)
    growth = serializers.FloatField()  # Yüzde


class CategoryRevenueSerializer(serializers.Serializer):
    """Kategori bazlı gelir."""
    category = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    percentage = serializers.FloatField()
    color = serializers.CharField()


class InstructorEarningsSerializer(serializers.Serializer):
    """Eğitmen kazançları."""
    id = serializers.IntegerField()
    name = serializers.CharField()
    avatar = serializers.CharField(required=False, allow_null=True)
    academy = serializers.CharField()
    totalEarnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthlyEarnings = serializers.DecimalField(max_digits=12, decimal_places=2)
    students = serializers.IntegerField()
    courses = serializers.IntegerField()


# =============================================================================
# GLOBAL LIVE SESSIONS SERIALIZER (Super Admin)
# =============================================================================

class GlobalLiveSessionSerializer(serializers.Serializer):
    """Global canlı ders serializeri."""
    id = serializers.IntegerField()
    title = serializers.CharField()
    instructor = serializers.CharField()
    instructorAvatar = serializers.CharField(required=False, allow_null=True)
    academy = serializers.CharField()
    academyLogo = serializers.CharField(required=False, allow_null=True)
    scheduledAt = serializers.DateTimeField()
    duration = serializers.IntegerField()  # Dakika
    status = serializers.ChoiceField(choices=['SCHEDULED', 'LIVE', 'COMPLETED', 'CANCELLED'])
    participantCount = serializers.IntegerField()
    maxParticipants = serializers.IntegerField()

