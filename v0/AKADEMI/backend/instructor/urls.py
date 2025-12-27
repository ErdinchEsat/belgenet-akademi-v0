"""
Instructor API URLs
===================
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InstructorDashboardView,
    InstructorClassViewSet,
    InstructorStudentViewSet,
    InstructorAssessmentViewSet,
    BehaviorAnalysisViewSet,
    CalendarViewSet,
    LiveStreamViewSet,
)

app_name = 'instructor'

router = DefaultRouter()
router.register('classes', InstructorClassViewSet, basename='classes')
router.register('students', InstructorStudentViewSet, basename='students')
router.register('assessments', InstructorAssessmentViewSet, basename='assessments')
router.register('behavior', BehaviorAnalysisViewSet, basename='behavior')
router.register('calendar', CalendarViewSet, basename='calendar')

urlpatterns = [
    path('dashboard/', InstructorDashboardView.as_view(), name='dashboard'),
    path('', include(router.urls)),
]

# Live stream URLs (separate from instructor namespace)
live_router = DefaultRouter()
live_router.register('', LiveStreamViewSet, basename='live')

