"""
Instructor API Views
====================

API endpoints for instructor-specific operations:
- Dashboard
- My Classes
- My Students
- Assessments
- Behavior Analysis
- Calendar

Gerçek veritabanı sorguları kullanılıyor.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum, F
from django.db.models.functions import Coalesce
from datetime import timedelta
import logging

from backend.student.models import (
    ClassGroup, ClassEnrollment, Assignment, AssignmentSubmission,
    LiveSession, Notification
)
from backend.courses.models import Course, Enrollment, ContentProgress
from backend.users.models import User

from .serializers import (
    InstructorDashboardSerializer,
    InstructorClassSerializer,
    InstructorStudentSerializer,
    StudentDetailSerializer,
    AssessmentSerializer,
    StudentBehaviorSerializer,
    ClassPerformanceSerializer,
    CalendarEventSerializer,
)

logger = logging.getLogger(__name__)


class InstructorDashboardView(APIView):
    """
    GET /api/v1/instructor/dashboard/
    Returns dashboard data for the instructor
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Eğitmenin sınıfları - ID'leri al (subquery optimizasyonu için)
        my_classes_ids = ClassGroup.objects.filter(
            instructors=user,
            status=ClassGroup.Status.ACTIVE
        ).values_list('id', flat=True)
        
        # Eğitmenin sınıfları - detaylı (schedule için)
        my_classes = ClassGroup.objects.filter(
            id__in=my_classes_ids
        ).select_related(
            'course',
        ).prefetch_related(
            'class_enrollments',
        )
        
        # Toplam öğrenci sayısı (benzersiz) - optimize edilmiş
        total_students = ClassEnrollment.objects.filter(
            class_group_id__in=my_classes_ids,
            status=ClassEnrollment.Status.ACTIVE
        ).values('user').distinct().count()

        # Bugünkü canlı dersler - select_related ile
        todays_live_sessions = LiveSession.objects.filter(
            instructor=user,
            scheduled_at__gte=today_start,
            scheduled_at__lt=today_end
        ).select_related(
            'class_group',
        ).order_by('scheduled_at')

        # Bekleyen ödevler (değerlendirilmemiş) - optimize edilmiş
        pending_submissions = AssignmentSubmission.objects.filter(
            assignment__class_group_id__in=my_classes_ids,
            status=AssignmentSubmission.Status.SUBMITTED
        ).count()

        # Bugünün programı
        today_schedule = []
        
        # Canlı dersler
        for session in todays_live_sessions[:5]:
            today_schedule.append({
                'id': str(session.id),
                'title': session.title,
                'type': 'live',
                'time': session.scheduled_at.strftime('%H:%M'),
                'className': session.class_group.name,
                'studentCount': session.class_group.student_count,
            })

        # Bugün teslim tarihi olan ödevler - select_related ile
        todays_assignments = Assignment.objects.filter(
            class_group_id__in=my_classes_ids,
            due_date__gte=today_start,
            due_date__lt=today_end,
            status=Assignment.Status.PUBLISHED
        ).select_related('class_group')
        
        for assignment in todays_assignments[:3]:
            today_schedule.append({
                'id': str(assignment.id),
                'title': f'{assignment.title} Son Teslim',
                'type': 'assignment',
                'time': assignment.due_date.strftime('%H:%M'),
                'className': assignment.class_group.name,
            })

        # Son aktiviteler
        recent_activities = []
        
        # Son ödev teslimleri - select_related ile assignment.class_group da ekle
        recent_submissions = AssignmentSubmission.objects.filter(
            assignment__class_group_id__in=my_classes_ids,
            submitted_at__isnull=False
        ).select_related(
            'student', 
            'assignment',
            'assignment__class_group',
        ).order_by('-submitted_at')[:5]
        
        for submission in recent_submissions:
            time_diff = now - submission.submitted_at
            if time_diff.days > 0:
                time_str = f'{time_diff.days} gün önce'
            elif time_diff.seconds > 3600:
                time_str = f'{time_diff.seconds // 3600} saat önce'
            else:
                time_str = f'{time_diff.seconds // 60} dk önce'
            
            recent_activities.append({
                'id': str(submission.id),
                'type': 'submission',
                'message': f'{submission.student.first_name} {submission.student.last_name[0]}. ödev gönderdi',
                'time': time_str,
                'studentName': f'{submission.student.first_name} {submission.student.last_name[0]}.',
            })

        # İstatistikler
        # Tamamlama oranı (tüm kayıtlı öğrencilerin ortalama ilerleme yüzdesi)
        enrollments = Enrollment.objects.filter(
            course__instructors=user,
            status=Enrollment.Status.ACTIVE
        )
        avg_completion = enrollments.aggregate(avg=Avg('progress_percent'))['avg'] or 0

        # Ortalama skor
        avg_score = AssignmentSubmission.objects.filter(
            assignment__class_group__in=my_classes,
            status=AssignmentSubmission.Status.GRADED,
            score__isnull=False
        ).aggregate(avg=Avg('score'))['avg'] or 0

        # Devam oranı (son 7 günde canlı derslere katılım)
        week_ago = now - timedelta(days=7)
        total_sessions = LiveSession.objects.filter(
            instructor=user,
            scheduled_at__gte=week_ago,
            status=LiveSession.Status.COMPLETED
        ).count()
        
        # Basit devam oranı hesabı
        attendance_rate = 92 if total_sessions > 0 else 0  # TODO: Gerçek katılım takibi eklenecek

        data = {
            'summary': {
                'totalStudents': total_students,
                'activeClasses': my_classes.count(),
                'upcomingLessons': todays_live_sessions.filter(status=LiveSession.Status.SCHEDULED).count(),
                'pendingAssessments': pending_submissions,
            },
            'todaySchedule': today_schedule,
            'recentActivities': recent_activities[:10],
            'quickStats': {
                'completionRate': round(avg_completion),
                'avgScore': round(avg_score),
                'attendanceRate': attendance_rate,
            },
        }
        
        logger.info(f"[INSTRUCTOR] Dashboard loaded for {user.email}: {total_students} students, {my_classes.count()} classes")
        return Response(data)


class InstructorClassViewSet(viewsets.ViewSet):
    """
    GET /api/v1/instructor/classes/
    GET /api/v1/instructor/classes/{id}/
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        status_filter = request.query_params.get('status', 'active')
        
        # Annotate ile tek sorguda student_count ve avg_progress hesapla
        from django.db.models import Count, Avg, Q, Subquery, OuterRef
        from django.db.models.functions import Coalesce
        
        # Sonraki canlı ders subquery
        next_session_subquery = LiveSession.objects.filter(
            class_group=OuterRef('pk'),
            scheduled_at__gte=timezone.now(),
            status=LiveSession.Status.SCHEDULED
        ).order_by('scheduled_at').values('id')[:1]
        
        classes = ClassGroup.objects.filter(
            instructors=user
        ).select_related(
            'course', 
            'course__tenant',
            'tenant',
        ).prefetch_related(
            'class_enrollments__user',
            'live_sessions',
        ).annotate(
            active_student_count=Count(
                'class_enrollments',
                filter=Q(class_enrollments__status=ClassEnrollment.Status.ACTIVE),
                distinct=True
            ),
            next_session_id=Subquery(next_session_subquery),
        )
        
        if status_filter == 'active':
            classes = classes.filter(status=ClassGroup.Status.ACTIVE)
        elif status_filter == 'completed':
            classes = classes.filter(status=ClassGroup.Status.COMPLETED)

        # Next session bilgilerini bir seferde çek
        next_session_ids = [c.next_session_id for c in classes if c.next_session_id]
        next_sessions_map = {}
        if next_session_ids:
            next_sessions = LiveSession.objects.filter(id__in=next_session_ids)
            next_sessions_map = {s.id: s for s in next_sessions}

        result = []
        for cls in classes:
            next_session = next_sessions_map.get(cls.next_session_id)
            
            # Ortalama ilerleme - basitleştirilmiş
            avg_progress = 0
            if cls.course_id:
                enrollment_progress = Enrollment.objects.filter(
                    course_id=cls.course_id,
                    status=Enrollment.Status.ACTIVE
                ).aggregate(avg=Avg('progress_percent'))
                avg_progress = enrollment_progress['avg'] or 0

            result.append({
                'id': str(cls.id),
                'name': cls.name,
                'code': cls.code,
                'course': {
                    'id': str(cls.course.id),
                    'title': cls.course.title,
                },
                'studentCount': cls.active_student_count or cls.student_count,
                'schedule': cls.term or 'Belirlenmedi',
                'nextSession': {
                    'date': next_session.scheduled_at.strftime('%Y-%m-%d') if next_session else None,
                    'topic': next_session.title if next_session else None,
                } if next_session else None,
                'progress': round(avg_progress),
                'status': cls.status.lower(),
            })

        logger.info(f"[INSTRUCTOR] Classes loaded for {user.email}: {len(result)} classes")
        return Response({'results': result, 'count': len(result)})

    def retrieve(self, request, pk=None):
        user = request.user
        try:
            cls = ClassGroup.objects.select_related('course', 'tenant').get(
                id=pk,
                instructors=user
            )
        except ClassGroup.DoesNotExist:
            return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)

        # Öğrenciler
        students = []
        for enrollment in cls.class_enrollments.filter(status=ClassEnrollment.Status.ACTIVE).select_related('user'):
            student = enrollment.user
            
            # Öğrencinin bu kurstaki ilerlemesi
            course_enrollment = Enrollment.objects.filter(
                user=student,
                course=cls.course
            ).first()
            
            # Öğrencinin bu sınıftaki ödev ortalaması
            avg_score = AssignmentSubmission.objects.filter(
                student=student,
                assignment__class_group=cls,
                status=AssignmentSubmission.Status.GRADED
            ).aggregate(avg=Avg('score'))['avg'] or 0

            students.append({
                'id': str(student.id),
                'name': f'{student.first_name} {student.last_name}',
                'email': student.email,
                'avatar': f'https://ui-avatars.com/api/?name={student.first_name}+{student.last_name}&background=random',
                'progress': course_enrollment.progress_percent if course_enrollment else 0,
                'avgScore': round(avg_score),
            })

        # Sonraki canlı ders
        next_session = LiveSession.objects.filter(
            class_group=cls,
            scheduled_at__gte=timezone.now(),
            status=LiveSession.Status.SCHEDULED
        ).order_by('scheduled_at').first()

        # Ödevler
        assignments = []
        for assignment in cls.assignments.filter(status=Assignment.Status.PUBLISHED).order_by('-due_date')[:5]:
            submission_count = assignment.submissions.filter(
                status__in=[AssignmentSubmission.Status.SUBMITTED, AssignmentSubmission.Status.GRADED]
            ).count()
            assignments.append({
                'id': str(assignment.id),
                'title': assignment.title,
                'dueDate': assignment.due_date.strftime('%Y-%m-%d'),
                'submissions': submission_count,
                'totalStudents': cls.student_count,
            })

        avg_progress = Enrollment.objects.filter(
            course=cls.course,
            user__in=cls.students.all(),
            status=Enrollment.Status.ACTIVE
        ).aggregate(avg=Avg('progress_percent'))['avg'] or 0

        class_data = {
            'id': str(cls.id),
            'name': cls.name,
            'code': cls.code,
            'course': {
                'id': str(cls.course.id),
                'title': cls.course.title,
                'description': cls.course.short_description,
            },
            'studentCount': cls.student_count,
            'schedule': cls.term or 'Belirlenmedi',
            'nextSession': {
                'date': next_session.scheduled_at.strftime('%Y-%m-%d') if next_session else None,
                'time': next_session.scheduled_at.strftime('%H:%M') if next_session else None,
                'topic': next_session.title if next_session else None,
            } if next_session else None,
            'progress': round(avg_progress),
            'status': cls.status.lower(),
            'students': students,
            'assignments': assignments,
        }
        
        return Response(class_data)


class InstructorStudentViewSet(viewsets.ViewSet):
    """
    GET /api/v1/instructor/students/
    GET /api/v1/instructor/students/{id}/
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        search = request.query_params.get('search', '')
        status_filter = request.query_params.get('status', '')
        course_filter = request.query_params.get('course', '')

        # Eğitmenin sınıflarının ID'leri (optimize edilmiş)
        my_classes_ids = ClassGroup.objects.filter(
            instructors=user,
            status=ClassGroup.Status.ACTIVE
        ).values_list('id', flat=True)
        
        # Benzersiz öğrenci ID'leri
        student_ids = ClassEnrollment.objects.filter(
            class_group_id__in=my_classes_ids,
            status=ClassEnrollment.Status.ACTIVE
        ).values_list('user_id', flat=True).distinct()

        # Annotate ile enrolled_courses ve avg_score hesapla
        from django.db.models import Count, Avg, Q
        
        students_qs = User.objects.filter(
            id__in=student_ids,
            role=User.Role.STUDENT
        ).annotate(
            enrolled_courses_count=Count(
                'enrollments',
                filter=Q(
                    enrollments__course__instructors=user,
                    enrollments__status=Enrollment.Status.ACTIVE
                ),
                distinct=True
            ),
            avg_score_computed=Avg(
                'assignment_submissions__score',
                filter=Q(
                    assignment_submissions__assignment__class_group_id__in=my_classes_ids,
                    assignment_submissions__status=AssignmentSubmission.Status.GRADED
                )
            )
        )

        # Arama filtresi
        if search:
            students_qs = students_qs.filter(
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        result = []
        now = timezone.now()
        
        for student in students_qs[:50]:  # Limit
            # Annotate'den aldığımız değerler
            enrolled_courses = student.enrolled_courses_count or 0
            avg_score = student.avg_score_computed or 0
            
            # Son aktivite
            last_activity = student.last_login
            if last_activity:
                diff = now - last_activity
                if diff.days > 7:
                    last_active = f'{diff.days // 7} hafta önce'
                    student_status = 'at_risk' if diff.days > 14 else 'inactive'
                elif diff.days > 0:
                    last_active = f'{diff.days} gün önce'
                    student_status = 'inactive' if diff.days > 3 else 'active'
                elif diff.seconds > 3600:
                    last_active = f'{diff.seconds // 3600} saat önce'
                    student_status = 'active'
                else:
                    last_active = f'{diff.seconds // 60} dk önce'
                    student_status = 'active'
            else:
                last_active = 'Hiç giriş yapmadı'
                student_status = 'at_risk'

            # Skor bazlı risk durumu
            if avg_score < 50 and avg_score > 0:
                student_status = 'at_risk'

            # Filtre uygula
            if status_filter and status_filter != student_status:
                continue

            result.append({
                'id': str(student.id),
                'name': f'{student.first_name} {student.last_name}',
                'email': student.email,
                'avatar': f'https://ui-avatars.com/api/?name={student.first_name}+{student.last_name}&background=random',
                'enrolledCourses': enrolled_courses,
                'avgScore': round(avg_score),
                'attendance': 90,  # TODO: Gerçek devam hesabı
                'lastActive': last_active,
                'status': student_status,
            })

        logger.info(f"[INSTRUCTOR] Students loaded for {user.email}: {len(result)} students")
        return Response({'results': result, 'count': len(result)})

    def retrieve(self, request, pk=None):
        user = request.user
        
        try:
            student = User.objects.get(id=pk, role=User.Role.STUDENT)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

        # Eğitmenin bu öğrenciye erişimi var mı?
        my_classes = ClassGroup.objects.filter(instructors=user)
        has_access = ClassEnrollment.objects.filter(
            user=student,
            class_group__in=my_classes
        ).exists()
        
        if not has_access:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        # Öğrencinin kursları
        courses = []
        enrollments = Enrollment.objects.filter(
            user=student,
            course__instructors=user
        ).select_related('course')
        
        for enrollment in enrollments:
            # Bu kurstaki ödev ortalaması
            avg_score = AssignmentSubmission.objects.filter(
                student=student,
                assignment__class_group__course=enrollment.course,
                status=AssignmentSubmission.Status.GRADED
            ).aggregate(avg=Avg('score'))['avg'] or 0

            courses.append({
                'id': str(enrollment.course.id),
                'title': enrollment.course.title,
                'progress': enrollment.progress_percent,
                'score': round(avg_score),
            })

        # Son aktiviteler
        recent_activity = []
        
        # Son ödev teslimleri
        submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment__class_group__in=my_classes,
            submitted_at__isnull=False
        ).select_related('assignment').order_by('-submitted_at')[:5]
        
        now = timezone.now()
        for submission in submissions:
            diff = now - submission.submitted_at
            if diff.days > 0:
                time_str = f'{diff.days} gün önce'
            elif diff.seconds > 3600:
                time_str = f'{diff.seconds // 3600} saat önce'
            else:
                time_str = f'{diff.seconds // 60} dk önce'
            
            recent_activity.append({
                'id': str(submission.id),
                'type': 'submission',
                'message': f'{submission.assignment.title} teslim edildi',
                'time': time_str,
            })

        # Değerlendirmeler
        assessments = []
        graded_submissions = AssignmentSubmission.objects.filter(
            student=student,
            assignment__class_group__in=my_classes,
            status=AssignmentSubmission.Status.GRADED
        ).select_related('assignment').order_by('-graded_at')[:10]
        
        for submission in graded_submissions:
            assessments.append({
                'type': 'assignment',
                'title': submission.assignment.title,
                'score': submission.score,
                'date': submission.graded_at.strftime('%Y-%m-%d') if submission.graded_at else None,
            })

        student_data = {
            'id': str(student.id),
            'name': f'{student.first_name} {student.last_name}',
            'email': student.email,
            'avatar': f'https://ui-avatars.com/api/?name={student.first_name}+{student.last_name}&background=random',
            'phone': '',  # Privacy
            'enrollmentDate': student.date_joined.strftime('%Y-%m-%d'),
            'courses': courses,
            'recentActivity': recent_activity,
            'assessments': assessments,
        }
        
        return Response(student_data)


class InstructorAssessmentViewSet(viewsets.ViewSet):
    """
    GET /api/v1/instructor/assessments/
    GET /api/v1/instructor/assessments/{id}/
    POST /api/v1/instructor/assessments/{id}/grade/
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        
        my_classes = ClassGroup.objects.filter(
            instructors=user,
            status=ClassGroup.Status.ACTIVE
        )

        # Ödevler
        assignments = Assignment.objects.filter(
            class_group__in=my_classes
        ).select_related('class_group', 'class_group__course').order_by('-due_date')

        result = []
        for assignment in assignments[:20]:
            # Teslim sayısı
            submission_stats = assignment.submissions.aggregate(
                total=Count('id'),
                graded=Count('id', filter=Q(status=AssignmentSubmission.Status.GRADED)),
                submitted=Count('id', filter=Q(status=AssignmentSubmission.Status.SUBMITTED)),
            )
            
            # Ortalama puan
            avg_score = assignment.submissions.filter(
                status=AssignmentSubmission.Status.GRADED
            ).aggregate(avg=Avg('score'))['avg']

            # Durum belirleme
            now = timezone.now()
            if submission_stats['submitted'] > 0:
                ass_status = 'grading'
            elif assignment.due_date < now:
                ass_status = 'completed'
            else:
                ass_status = 'pending'

            result.append({
                'id': str(assignment.id),
                'title': assignment.title,
                'type': 'assignment',
                'course': {
                    'id': str(assignment.class_group.course.id),
                    'title': assignment.class_group.course.title,
                },
                'class': {
                    'id': str(assignment.class_group.id),
                    'name': assignment.class_group.name,
                },
                'dueDate': assignment.due_date.strftime('%Y-%m-%d'),
                'submissions': submission_stats['submitted'] + submission_stats['graded'],
                'totalStudents': assignment.class_group.student_count,
                'avgScore': round(avg_score) if avg_score else None,
                'status': ass_status,
            })

        logger.info(f"[INSTRUCTOR] Assessments loaded for {user.email}: {len(result)} items")
        return Response({'results': result, 'count': len(result)})

    def retrieve(self, request, pk=None):
        user = request.user
        
        try:
            assignment = Assignment.objects.select_related(
                'class_group', 'class_group__course'
            ).get(id=pk, class_group__instructors=user)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

        # Teslimler
        submissions = []
        for submission in assignment.submissions.select_related('student').order_by('-submitted_at'):
            submissions.append({
                'id': str(submission.id),
                'studentId': str(submission.student.id),
                'studentName': f'{submission.student.first_name} {submission.student.last_name}',
                'status': submission.status,
                'submittedAt': submission.submitted_at.isoformat() if submission.submitted_at else None,
                'score': submission.score,
                'feedback': submission.feedback,
            })

        submission_stats = assignment.submissions.aggregate(
            total=Count('id'),
            graded=Count('id', filter=Q(status=AssignmentSubmission.Status.GRADED)),
            submitted=Count('id', filter=Q(status=AssignmentSubmission.Status.SUBMITTED)),
        )
        
        avg_score = assignment.submissions.filter(
            status=AssignmentSubmission.Status.GRADED
        ).aggregate(avg=Avg('score'))['avg']

        assessment_data = {
            'id': str(assignment.id),
            'title': assignment.title,
            'description': assignment.description,
            'type': 'assignment',
            'course': {
                'id': str(assignment.class_group.course.id),
                'title': assignment.class_group.course.title,
            },
            'class': {
                'id': str(assignment.class_group.id),
                'name': assignment.class_group.name,
            },
            'dueDate': assignment.due_date.strftime('%Y-%m-%d'),
            'maxScore': assignment.max_score,
            'submissions': submissions,
            'stats': {
                'total': submission_stats['total'],
                'submitted': submission_stats['submitted'],
                'graded': submission_stats['graded'],
                'avgScore': round(avg_score) if avg_score else None,
            },
        }
        
        return Response(assessment_data)

    @action(detail=True, methods=['post'])
    def grade(self, request, pk=None):
        user = request.user
        grades = request.data.get('grades', [])
        
        try:
            assignment = Assignment.objects.get(id=pk, class_group__instructors=user)
        except Assignment.DoesNotExist:
            return Response({'error': 'Assessment not found'}, status=status.HTTP_404_NOT_FOUND)

        graded_count = 0
        for grade_data in grades:
            submission_id = grade_data.get('submissionId')
            score = grade_data.get('score')
            feedback = grade_data.get('feedback', '')
            
            try:
                submission = AssignmentSubmission.objects.get(
                    id=submission_id,
                    assignment=assignment
                )
                submission.score = score
                submission.feedback = feedback
                submission.status = AssignmentSubmission.Status.GRADED
                submission.graded_by = user
                submission.graded_at = timezone.now()
                submission.save()
                graded_count += 1
            except AssignmentSubmission.DoesNotExist:
                continue

        logger.info(f"[INSTRUCTOR] Graded {graded_count} submissions for assignment {pk}")
        return Response({'message': f'{graded_count} ödev notlandırıldı'})


class BehaviorAnalysisViewSet(viewsets.ViewSet):
    """
    GET /api/v1/instructor/behavior/students/
    GET /api/v1/instructor/behavior/classes/
    GET /api/v1/instructor/behavior/content-issues/
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='students')
    def students(self, request):
        user = request.user
        
        my_classes = ClassGroup.objects.filter(
            instructors=user,
            status=ClassGroup.Status.ACTIVE
        )
        
        student_ids = ClassEnrollment.objects.filter(
            class_group__in=my_classes,
            status=ClassEnrollment.Status.ACTIVE
        ).values_list('user_id', flat=True).distinct()

        students = User.objects.filter(id__in=student_ids, role=User.Role.STUDENT)
        now = timezone.now()
        
        result = []
        for student in students[:30]:
            # İlerleme ve skor hesapla
            enrollments = Enrollment.objects.filter(
                user=student,
                course__instructors=user,
                status=Enrollment.Status.ACTIVE
            )
            
            avg_progress = enrollments.aggregate(avg=Avg('progress_percent'))['avg'] or 0
            
            avg_score = AssignmentSubmission.objects.filter(
                student=student,
                assignment__class_group__in=my_classes,
                status=AssignmentSubmission.Status.GRADED
            ).aggregate(avg=Avg('score'))['avg'] or 0

            # İzleme süresi (toplam dakika)
            watch_time = ContentProgress.objects.filter(
                enrollment__user=student,
                enrollment__course__instructors=user
            ).aggregate(total=Sum('watched_seconds'))['total'] or 0
            watch_time_hours = round(watch_time / 3600, 1)

            # Risk seviyesi
            if avg_score < 50 or avg_progress < 30:
                risk_level = 'high'
                trend = 'declining'
            elif avg_score < 70 or avg_progress < 60:
                risk_level = 'medium'
                trend = 'stable'
            else:
                risk_level = 'low'
                trend = 'improving'

            # Son aktivite
            last_activity = student.last_login
            if last_activity:
                diff = now - last_activity
                if diff.days > 7:
                    last_active = f'{diff.days // 7} hafta önce'
                elif diff.days > 0:
                    last_active = f'{diff.days} gün önce'
                elif diff.seconds > 3600:
                    last_active = f'{diff.seconds // 3600} saat önce'
                else:
                    last_active = f'{diff.seconds // 60} dk önce'
            else:
                last_active = 'Hiç giriş yapmadı'

            result.append({
                'id': str(student.id),
                'name': f'{student.first_name} {student.last_name}',
                'avatar': f'https://ui-avatars.com/api/?name={student.first_name}+{student.last_name}&background=random',
                'watchTime': watch_time_hours,
                'completionRate': round(avg_progress),
                'avgScore': round(avg_score),
                'riskLevel': risk_level,
                'trend': trend,
                'lastActivity': last_active,
            })

        # Risk seviyesine göre sırala
        risk_order = {'high': 0, 'medium': 1, 'low': 2}
        result.sort(key=lambda x: risk_order.get(x['riskLevel'], 3))

        return Response({'results': result, 'count': len(result)})

    @action(detail=False, methods=['get'], url_path='classes')
    def classes(self, request):
        user = request.user
        
        my_classes = ClassGroup.objects.filter(
            instructors=user,
            status=ClassGroup.Status.ACTIVE
        ).select_related('course')

        result = []
        for cls in my_classes:
            # Sınıf istatistikleri
            student_ids = cls.class_enrollments.filter(
                status=ClassEnrollment.Status.ACTIVE
            ).values_list('user_id', flat=True)

            # Ortalama ilerleme
            avg_progress = Enrollment.objects.filter(
                user_id__in=student_ids,
                course=cls.course,
                status=Enrollment.Status.ACTIVE
            ).aggregate(avg=Avg('progress_percent'))['avg'] or 0

            # Ortalama skor
            avg_score = AssignmentSubmission.objects.filter(
                student_id__in=student_ids,
                assignment__class_group=cls,
                status=AssignmentSubmission.Status.GRADED
            ).aggregate(avg=Avg('score'))['avg'] or 0

            result.append({
                'id': str(cls.id),
                'name': cls.name,
                'avgScore': round(avg_score),
                'completionRate': round(avg_progress),
                'attendanceRate': 90,  # TODO: Gerçek devam hesabı
                'studentCount': cls.student_count,
            })

        return Response(result)

    @action(detail=False, methods=['get'], url_path='content-issues')
    def content_issues(self, request):
        user = request.user
        
        # İçerik sorunlarını tespit et
        # Düşük tamamlama oranına sahip içerikler
        issues = []
        
        my_courses = Course.objects.filter(instructors=user)
        
        for course in my_courses:
            # Her modül için içerik istatistikleri
            for module in course.modules.all():
                for content in module.contents.all():
                    # Bu içeriği başlatan öğrenci sayısı
                    started = ContentProgress.objects.filter(
                        content=content
                    ).count()
                    
                    # Tamamlayan öğrenci sayısı
                    completed = ContentProgress.objects.filter(
                        content=content,
                        is_completed=True
                    ).count()
                    
                    if started > 5:  # En az 5 öğrenci başlamış olmalı
                        completion_rate = (completed / started) * 100
                        
                        if completion_rate < 50:
                            issues.append({
                                'id': str(content.id),
                                'content': content.title,
                                'issue': 'Yüksek terk oranı' if completion_rate < 30 else 'Düşük tamamlama',
                                'studentCount': started - completed,
                                'completionRate': round(completion_rate),
                            })

        # En sorunlu içerikleri öne çıkar
        issues.sort(key=lambda x: x.get('completionRate', 100))
        
        return Response(issues[:10])


class CalendarViewSet(viewsets.ViewSet):
    """
    GET /api/v1/instructor/calendar/
    POST /api/v1/instructor/calendar/
    PATCH /api/v1/instructor/calendar/{id}/
    DELETE /api/v1/instructor/calendar/{id}/
    """
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        
        # Tarih aralığı
        start_date = request.query_params.get('start')
        end_date = request.query_params.get('end')
        
        now = timezone.now()
        if not start_date:
            start_date = now - timedelta(days=30)
        if not end_date:
            end_date = now + timedelta(days=60)

        events = []
        
        # Canlı dersler
        live_sessions = LiveSession.objects.filter(
            instructor=user,
            scheduled_at__gte=start_date,
            scheduled_at__lte=end_date
        ).select_related('class_group')
        
        for session in live_sessions:
            events.append({
                'id': f'live-{session.id}',
                'title': session.title,
                'type': 'live',
                'start': session.scheduled_at.isoformat(),
                'end': (session.scheduled_at + timedelta(minutes=session.duration_minutes)).isoformat(),
                'className': session.class_group.name,
                'color': '#6366f1',  # Indigo
                'status': session.status,
            })

        # Ödev teslim tarihleri
        my_classes = ClassGroup.objects.filter(instructors=user)
        assignments = Assignment.objects.filter(
            class_group__in=my_classes,
            due_date__gte=start_date,
            due_date__lte=end_date,
            status=Assignment.Status.PUBLISHED
        ).select_related('class_group')
        
        for assignment in assignments:
            events.append({
                'id': f'assignment-{assignment.id}',
                'title': f'{assignment.title} Teslim',
                'type': 'assignment',
                'start': assignment.due_date.isoformat(),
                'end': assignment.due_date.isoformat(),
                'className': assignment.class_group.name,
                'color': '#f59e0b',  # Amber
            })

        return Response(events)

    def create(self, request):
        user = request.user
        data = request.data
        
        event_type = data.get('type', 'live')
        
        if event_type == 'live':
            # Canlı ders oluştur
            try:
                class_group = ClassGroup.objects.get(
                    id=data.get('classId'),
                    instructors=user
                )
            except ClassGroup.DoesNotExist:
                return Response({'error': 'Class not found'}, status=status.HTTP_404_NOT_FOUND)

            session = LiveSession.objects.create(
                title=data.get('title', 'Canlı Ders'),
                description=data.get('description', ''),
                class_group=class_group,
                instructor=user,
                scheduled_at=data.get('start'),
                duration_minutes=data.get('duration', 60),
                meeting_url=data.get('meetingUrl', ''),
            )
            
            return Response({
                'id': f'live-{session.id}',
                'title': session.title,
                'type': 'live',
                'start': session.scheduled_at.isoformat(),
                'className': class_group.name,
            }, status=status.HTTP_201_CREATED)

        return Response({'error': 'Unsupported event type'}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        user = request.user
        data = request.data
        
        if pk.startswith('live-'):
            session_id = pk.replace('live-', '')
            try:
                session = LiveSession.objects.get(id=session_id, instructor=user)
                
                if 'title' in data:
                    session.title = data['title']
                if 'start' in data:
                    session.scheduled_at = data['start']
                if 'duration' in data:
                    session.duration_minutes = data['duration']
                
                session.save()
                
                return Response({
                    'id': pk,
                    'title': session.title,
                    'start': session.scheduled_at.isoformat(),
                })
            except LiveSession.DoesNotExist:
                return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        user = request.user
        
        if pk.startswith('live-'):
            session_id = pk.replace('live-', '')
            try:
                session = LiveSession.objects.get(id=session_id, instructor=user)
                session.status = LiveSession.Status.CANCELLED
                session.save()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except LiveSession.DoesNotExist:
                pass

        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)


class LiveStreamViewSet(viewsets.ViewSet):
    """
    GET /api/v1/live/{session_id}/participants/
    GET /api/v1/live/{session_id}/messages/
    POST /api/v1/live/{session_id}/messages/
    """
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'], url_path='participants')
    def participants(self, request, pk=None):
        try:
            session = LiveSession.objects.get(id=pk)
        except LiveSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)

        # Sınıftaki öğrencileri listele
        participants = []
        for enrollment in session.class_group.class_enrollments.filter(
            status=ClassEnrollment.Status.ACTIVE
        ).select_related('user')[:50]:
            student = enrollment.user
            participants.append({
                'id': str(student.id),
                'name': f'{student.first_name} {student.last_name}',
                'avatar': f'https://ui-avatars.com/api/?name={student.first_name}+{student.last_name}&background=random',
                'joinedAt': timezone.now().isoformat(),  # TODO: Gerçek katılım zamanı
            })

        return Response(participants)

    @action(detail=True, methods=['get', 'post'], url_path='messages')
    def messages(self, request, pk=None):
        if request.method == 'POST':
            # TODO: Gerçek mesaj kaydetme
            return Response({'status': 'sent'}, status=status.HTTP_201_CREATED)
        
        # TODO: Gerçek mesajları getir
        messages = []
        return Response(messages)
