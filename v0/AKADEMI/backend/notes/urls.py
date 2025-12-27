"""
Notes URL Configuration
=======================

Notes API endpoint'leri.

URL Patterns:
    /api/v1/courses/{courseId}/content/{contentId}/notes/
    /api/v1/courses/{courseId}/content/{contentId}/bookmarks/
    /api/v1/notes/export/
    /api/v1/notes/shared/{token}/
"""

from django.urls import path

from .views import (
    NotesListView,
    NoteDetailView,
    NoteRepliesView,
    NoteReactionView,
    NoteShareView,
    SharedNoteView,
    BookmarksView,
    NotesExportView,
)

app_name = 'notes'

# Content scoped URLs (courses/{courseId}/content/{contentId}/ prefix ile)
content_urlpatterns = [
    path('notes/', NotesListView.as_view(), name='list'),
    path('notes/<uuid:note_id>/', NoteDetailView.as_view(), name='detail'),
    path('notes/<uuid:note_id>/replies/', NoteRepliesView.as_view(), name='replies'),
    path('notes/<uuid:note_id>/react/', NoteReactionView.as_view(), name='react'),
    path('notes/<uuid:note_id>/share/', NoteShareView.as_view(), name='share'),
    path('bookmarks/', BookmarksView.as_view(), name='bookmarks'),
]

# Global URLs
urlpatterns = [
    path('export/', NotesExportView.as_view(), name='export'),
    path('shared/<str:token>/', SharedNoteView.as_view(), name='shared'),
]

