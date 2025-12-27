"""
Notes Views
===========

Notes API endpoint'leri.
"""

import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession

from .models import VideoNote, NoteReply, NoteReaction
from .serializers import (
    NoteCreateSerializer,
    NoteUpdateSerializer,
    NoteResponseSerializer,
    NoteListSerializer,
    ReplyCreateSerializer,
    ReplyResponseSerializer,
    ReactionSerializer,
    NoteShareSerializer,
    NotesExportSerializer,
    NotesExportResponseSerializer,
)
from .services import NotesService

logger = logging.getLogger(__name__)


class NotesListView(APIView):
    """
    Notes List/Create API.
    
    Endpoints:
        GET  /notes/  → Kullanıcının notlarını listele
        POST /notes/  → Yeni not oluştur
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
        Kullanıcının notlarını listele.
        
        Query params:
            note_type: Filtre (note, question, highlight, bookmark)
            include_public: Public notları dahil et
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        note_type = request.query_params.get('note_type')
        include_public = request.query_params.get('include_public', '').lower() == 'true'
        
        notes = NotesService.get_user_notes(
            user=request.user,
            content=content,
            note_type=note_type,
            include_public=include_public,
        )
        
        serializer = NoteListSerializer(notes, many=True)
        
        return Response({
            'content_id': content.id,
            'total': len(notes),
            'notes': serializer.data,
        })
    
    def post(self, request, course_id, content_id):
        """
        Yeni not oluştur.
        
        Request:
        {
            "note_type": "note",
            "content_text": "Bu önemli bir nokta",
            "video_ts": 120,
            "visibility": "private",
            "tags": ["önemli", "soru"]
        }
        """
        course, content = self.get_course_and_content(request, course_id, content_id)
        
        serializer = NoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Session al (opsiyonel)
        session = None
        if data.get('session_id'):
            try:
                session = PlaybackSession.objects.get(
                    id=data['session_id'],
                    user=request.user,
                )
            except PlaybackSession.DoesNotExist:
                pass
        
        note = NotesService.create_note(
            user=request.user,
            course=course,
            content=content,
            session=session,
            note_type=data.get('note_type', VideoNote.NoteType.NOTE),
            content_text=data.get('content_text', ''),
            video_ts=data.get('video_ts'),
            video_ts_end=data.get('video_ts_end'),
            visibility=data.get('visibility', VideoNote.NoteVisibility.PRIVATE),
            color=data.get('color'),
            tags=data.get('tags', []),
        )
        
        response_serializer = NoteResponseSerializer(
            note, context={'request': request}
        )
        
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class NoteDetailView(APIView):
    """
    Note Detail API.
    
    Endpoints:
        GET    /notes/{noteId}/  → Not detayı
        PUT    /notes/{noteId}/  → Notu güncelle
        DELETE /notes/{noteId}/  → Notu sil
    """
    
    permission_classes = [IsAuthenticated]
    
    def get_note(self, request, note_id):
        """Notu al ve yetki kontrolü yap."""
        note = get_object_or_404(
            VideoNote.objects.select_related('user', 'course', 'content'),
            id=note_id,
            tenant=request.user.tenant,
        )
        return note
    
    def get(self, request, course_id, content_id, note_id):
        """Not detayını getir."""
        note = self.get_note(request, note_id)
        
        # Yetki kontrolü
        if (note.user != request.user and 
            note.visibility == VideoNote.NoteVisibility.PRIVATE):
            return Response(
                {'detail': 'Not bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = NoteResponseSerializer(note, context={'request': request})
        return Response(serializer.data)
    
    def put(self, request, course_id, content_id, note_id):
        """Notu güncelle."""
        note = self.get_note(request, note_id)
        
        # Sadece not sahibi güncelleyebilir
        if note.user != request.user:
            return Response(
                {'detail': 'Bu notu düzenleme yetkiniz yok'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = NoteUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        updated_note = NotesService.update_note(note, **serializer.validated_data)
        
        response_serializer = NoteResponseSerializer(
            updated_note, context={'request': request}
        )
        return Response(response_serializer.data)
    
    def delete(self, request, course_id, content_id, note_id):
        """Notu sil."""
        note = self.get_note(request, note_id)
        
        # Sadece not sahibi silebilir
        if note.user != request.user:
            return Response(
                {'detail': 'Bu notu silme yetkiniz yok'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        NotesService.delete_note(note)
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteRepliesView(APIView):
    """
    Note Replies API.
    
    Endpoints:
        GET  /notes/{noteId}/replies/  → Cevapları listele
        POST /notes/{noteId}/replies/  → Cevap ekle
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id, note_id):
        """Cevapları listele."""
        note = get_object_or_404(
            VideoNote,
            id=note_id,
            tenant=request.user.tenant,
        )
        
        # Yetki kontrolü
        if (note.user != request.user and 
            note.visibility == VideoNote.NoteVisibility.PRIVATE):
            return Response(
                {'detail': 'Not bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        replies = NotesService.get_replies(note)
        serializer = ReplyResponseSerializer(replies, many=True)
        
        return Response({
            'note_id': str(note.id),
            'total': len(replies),
            'replies': serializer.data,
        })
    
    def post(self, request, course_id, content_id, note_id):
        """Cevap ekle."""
        note = get_object_or_404(
            VideoNote,
            id=note_id,
            tenant=request.user.tenant,
        )
        
        # Private nota cevap verilemez (sahibi hariç)
        if (note.visibility == VideoNote.NoteVisibility.PRIVATE and 
            note.user != request.user):
            return Response(
                {'detail': 'Bu nota cevap veremezsiniz'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ReplyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        # Parent reply al
        parent = None
        if data.get('parent_id'):
            parent = NoteReply.objects.filter(
                id=data['parent_id'],
                note=note,
            ).first()
        
        reply = NotesService.add_reply(
            user=request.user,
            note=note,
            content_text=data['content_text'],
            parent=parent,
        )
        
        response_serializer = ReplyResponseSerializer(reply)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class NoteReactionView(APIView):
    """
    Note Reaction API.
    
    Endpoint:
        POST /notes/{noteId}/react/  → Reaksiyon ekle/kaldır
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id, content_id, note_id):
        """Reaksiyon toggle."""
        note = get_object_or_404(
            VideoNote,
            id=note_id,
            tenant=request.user.tenant,
        )
        
        serializer = ReactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        added, reaction = NotesService.toggle_reaction(
            user=request.user,
            reaction_type=serializer.validated_data['reaction_type'],
            note=note,
        )
        
        return Response({
            'added': added,
            'reaction_type': serializer.validated_data['reaction_type'],
            'like_count': note.like_count,
        })


class NoteShareView(APIView):
    """
    Note Share API.
    
    Endpoint:
        POST /notes/{noteId}/share/  → Notu paylaş
    """
    
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id, content_id, note_id):
        """Notu paylaş."""
        note = get_object_or_404(
            VideoNote,
            id=note_id,
            user=request.user,  # Sadece sahibi paylaşabilir
            tenant=request.user.tenant,
        )
        
        serializer = NoteShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        shared_note = NotesService.share_note(
            note=note,
            visibility=serializer.validated_data['visibility'],
        )
        
        return Response({
            'note_id': str(note.id),
            'visibility': shared_note.visibility,
            'share_token': shared_note.share_token,
            'share_url': f"/notes/shared/{shared_note.share_token}/",
        })


class SharedNoteView(APIView):
    """
    Shared Note View API.
    
    Endpoint:
        GET /notes/shared/{token}/  → Paylaşılan notu görüntüle
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, token):
        """Paylaşılan notu görüntüle."""
        note = NotesService.get_by_share_token(token)
        
        if not note:
            return Response(
                {'detail': 'Not bulunamadı'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = NoteResponseSerializer(note, context={'request': request})
        return Response(serializer.data)


class BookmarksView(APIView):
    """
    Bookmarks API.
    
    Endpoints:
        GET  /bookmarks/  → Yer işaretlerini listele
        POST /bookmarks/  → Hızlı yer işareti ekle
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, content_id):
        """Yer işaretlerini listele."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        bookmarks = NotesService.get_user_bookmarks(
            user=request.user,
            course=course,
        )
        
        serializer = NoteListSerializer(bookmarks, many=True)
        return Response({
            'course_id': course.id,
            'total': len(bookmarks),
            'bookmarks': serializer.data,
        })
    
    def post(self, request, course_id, content_id):
        """Hızlı yer işareti ekle."""
        course = get_object_or_404(
            Course.objects.filter(tenant=request.user.tenant),
            id=course_id
        )
        
        content = get_object_or_404(
            CourseContent.objects.filter(module__course=course),
            id=content_id
        )
        
        video_ts = request.data.get('video_ts', 0)
        
        bookmark = NotesService.quick_bookmark(
            user=request.user,
            content=content,
            video_ts=video_ts,
        )
        
        serializer = NoteResponseSerializer(bookmark, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class NotesExportView(APIView):
    """
    Notes Export API.
    
    Endpoints:
        GET  /notes/export/  → Export'ları listele
        POST /notes/export/  → Export talebi oluştur
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Export'ları listele."""
        exports = NotesService.get_user_exports(request.user)
        serializer = NotesExportResponseSerializer(exports, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Export talebi oluştur."""
        serializer = NotesExportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        
        course = None
        if data.get('course_id'):
            course = get_object_or_404(
                Course.objects.filter(tenant=request.user.tenant),
                id=data['course_id']
            )
        
        export = NotesService.request_export(
            user=request.user,
            format=data.get('format'),
            course=course,
        )
        
        response_serializer = NotesExportResponseSerializer(export)
        return Response(response_serializer.data, status=status.HTTP_202_ACCEPTED)

