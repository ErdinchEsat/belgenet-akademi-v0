"""
Sequencing Views
================

İçerik kilitleme API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent, Enrollment

from .serializers import LockStatusSerializer, EvaluateResponseSerializer
from .services import PolicyEngine

logger = logging.getLogger(__name__)


class LockStatusView(APIView):
    """
    Lock Status API.
    
    Endpoint:
        GET /lock/  → Kilit durumu sorgula
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_course_and_content(self, request, course_id, content_id):
        """URL'den course ve content objelerini al."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        return course, content
    
    def get(self, request, course_id, content_id):
        """
        Kilit durumunu sorgula.
        
        GET /api/v1/courses/{courseId}/content/{contentId}/lock/
        
        Response 200:
        {
            "content_id": 123,
            "is_unlocked": false,
            "unlocked_at": null,
            "requirements": [
                {"type": "min_watch_ratio", "passed": false, "details": {"current": 0.62, "required": 0.80}}
            ]
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Kilit durumunu al
        is_unlocked, requirements = PolicyEngine.get_lock_status(
            user=request.user,
            course=course,
            content=content,
        )
        
        # Unlock state'i al (unlocked_at için)
        from .models import ContentUnlockState
        try:
            unlock_state = ContentUnlockState.objects.get(
                tenant=request.user.tenant,
                user=request.user,
                content=content,
            )
            unlocked_at = unlock_state.unlocked_at
        except ContentUnlockState.DoesNotExist:
            unlocked_at = None
        
        response_data = {
            'content_id': content.id,
            'is_unlocked': is_unlocked,
            'unlocked_at': unlocked_at,
            'requirements': requirements,
        }
        
        return Response(response_data)


class LockEvaluateView(APIView):
    """
    Lock Evaluate API.
    
    Endpoint:
        POST /lock/evaluate/  → Kilit değerlendir
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_course_and_content(self, request, course_id, content_id):
        """URL'den course ve content objelerini al."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        return course, content
    
    def post(self, request, course_id, content_id):
        """
        Kilit değerlendirmesi yap.
        
        POST /api/v1/courses/{courseId}/content/{contentId}/lock/evaluate/
        
        Response 200:
        {
            "content_id": 123,
            "is_unlocked": true,
            "unlocked_at": "2025-12-26T10:20:00Z",
            "changed": true
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        # Kilit değerlendirmesi yap
        is_unlocked, changed = PolicyEngine.evaluate_unlock(
            user=request.user,
            course=course,
            content=content,
        )
        
        # Unlock state'i al
        from .models import ContentUnlockState
        try:
            unlock_state = ContentUnlockState.objects.get(
                tenant=request.user.tenant,
                user=request.user,
                content=content,
            )
            unlocked_at = unlock_state.unlocked_at
        except ContentUnlockState.DoesNotExist:
            unlocked_at = None
        
        response_data = {
            'content_id': content.id,
            'is_unlocked': is_unlocked,
            'unlocked_at': unlocked_at,
            'changed': changed,
        }
        
        return Response(response_data)

