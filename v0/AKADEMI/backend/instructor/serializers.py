"""
Instructor API Serializers
==========================
"""

from rest_framework import serializers
from backend.courses.models import Course, Enrollment
from backend.users.models import User


class InstructorSummarySerializer(serializers.Serializer):
    """Dashboard summary statistics"""
    totalStudents = serializers.IntegerField()
    activeClasses = serializers.IntegerField()
    upcomingLessons = serializers.IntegerField()
    pendingAssessments = serializers.IntegerField()


class ScheduleItemSerializer(serializers.Serializer):
    """Schedule item for dashboard"""
    id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.ChoiceField(choices=['live', 'assignment', 'exam', 'quiz'])
    time = serializers.CharField()
    className = serializers.CharField()
    studentCount = serializers.IntegerField(required=False)


class ActivityItemSerializer(serializers.Serializer):
    """Recent activity item"""
    id = serializers.CharField()
    type = serializers.ChoiceField(choices=['submission', 'question', 'attendance', 'grade'])
    message = serializers.CharField()
    time = serializers.CharField()
    studentName = serializers.CharField(required=False)


class QuickStatsSerializer(serializers.Serializer):
    """Quick stats for dashboard"""
    completionRate = serializers.IntegerField()
    avgScore = serializers.IntegerField()
    attendanceRate = serializers.IntegerField()


class InstructorDashboardSerializer(serializers.Serializer):
    """Full dashboard response"""
    summary = InstructorSummarySerializer()
    todaySchedule = ScheduleItemSerializer(many=True)
    recentActivities = ActivityItemSerializer(many=True)
    quickStats = QuickStatsSerializer()


class InstructorClassSerializer(serializers.Serializer):
    """Instructor's class"""
    id = serializers.CharField()
    name = serializers.CharField()
    code = serializers.CharField()
    course = serializers.DictField()
    studentCount = serializers.IntegerField()
    schedule = serializers.CharField()
    nextSession = serializers.DictField(required=False, allow_null=True)
    progress = serializers.IntegerField()
    status = serializers.ChoiceField(choices=['active', 'completed', 'upcoming'])


class InstructorStudentSerializer(serializers.Serializer):
    """Student in instructor's class"""
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(required=False, allow_null=True)
    enrolledCourses = serializers.IntegerField()
    avgScore = serializers.IntegerField()
    attendance = serializers.IntegerField()
    lastActive = serializers.CharField()
    status = serializers.ChoiceField(choices=['active', 'inactive', 'at_risk'])


class StudentDetailSerializer(serializers.Serializer):
    """Detailed student info"""
    id = serializers.CharField()
    name = serializers.CharField()
    email = serializers.EmailField()
    avatar = serializers.CharField(required=False, allow_null=True)
    phone = serializers.CharField(required=False, allow_null=True)
    enrollmentDate = serializers.CharField()
    courses = serializers.ListField()
    recentActivity = ActivityItemSerializer(many=True)
    assessments = serializers.ListField()


class AssessmentSerializer(serializers.Serializer):
    """Assessment item"""
    id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.ChoiceField(choices=['assignment', 'quiz', 'exam'])
    course = serializers.DictField()
    class_ = serializers.DictField(source='class')
    dueDate = serializers.CharField()
    submissions = serializers.IntegerField()
    totalStudents = serializers.IntegerField()
    avgScore = serializers.IntegerField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=['pending', 'grading', 'completed'])


class StudentBehaviorSerializer(serializers.Serializer):
    """Student behavior analysis"""
    id = serializers.CharField()
    name = serializers.CharField()
    avatar = serializers.CharField(required=False, allow_null=True)
    watchTime = serializers.IntegerField()
    completionRate = serializers.IntegerField()
    avgScore = serializers.IntegerField()
    riskLevel = serializers.ChoiceField(choices=['low', 'medium', 'high'])
    trend = serializers.ChoiceField(choices=['improving', 'stable', 'declining'])
    lastActivity = serializers.CharField()


class ClassPerformanceSerializer(serializers.Serializer):
    """Class performance metrics"""
    id = serializers.CharField()
    name = serializers.CharField()
    avgScore = serializers.IntegerField()
    completionRate = serializers.IntegerField()
    attendanceRate = serializers.IntegerField()
    studentCount = serializers.IntegerField()


class CalendarEventSerializer(serializers.Serializer):
    """Calendar event"""
    id = serializers.CharField()
    title = serializers.CharField()
    type = serializers.ChoiceField(choices=['live', 'assignment', 'exam', 'quiz', 'meeting'])
    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
    className = serializers.CharField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_null=True)
    color = serializers.CharField(required=False, allow_null=True)

