"""
Course URLs
===========

Kurs API endpoint'leri.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CourseViewSet,
    EnrollmentViewSet,
)

app_name = 'courses'

# Ana router
router = DefaultRouter()
router.register('', CourseViewSet, basename='course')
router.register('enrollments', EnrollmentViewSet, basename='enrollment')

# URL patterns
urlpatterns = [
    path('', include(router.urls)),
]

