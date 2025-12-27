"""
Notes Service
=============

Not yönetim servisi.
"""

import logging
import secrets
from typing import List, Dict, Optional
from django.db import transaction
from django.db.models import Q, F

from backend.courses.models import Course, CourseContent
from backend.player.models import PlaybackSession
from ..models import VideoNote, NoteReply, NoteReaction, NoteExport

logger = logging.getLogger(__name__)


class NotesService:
    """
    Not yönetim servisi.
    
    Sorumluluklar:
    - Not CRUD işlemleri
    - Thread yönetimi
    - Reaksiyon yönetimi
    - Paylaşım ve dışa aktarma
    """
    
    @classmethod
    @transaction.atomic
    def create_note(
        cls,
        user,
        course: Course,
        content: CourseContent,
        note_type: str = VideoNote.NoteType.NOTE,
        content_text: str = "",
        video_ts: int = None,
        video_ts_end: int = None,
        visibility: str = VideoNote.NoteVisibility.PRIVATE,
        color: str = None,
        tags: List[str] = None,
        session: PlaybackSession = None,
    ) -> VideoNote:
        """
        Yeni not oluştur.
        """
        note = VideoNote.objects.create(
            tenant=user.tenant,
            user=user,
            course=course,
            content=content,
            session=session,
            note_type=note_type,
            content_text=content_text,
            video_ts=video_ts,
            video_ts_end=video_ts_end,
            visibility=visibility,
            color=color,
            tags=tags or [],
        )
        
        logger.info(f"Note created: user={user.id}, content={content.id}, note={note.id}")
        
        return note
    
    @classmethod
    @transaction.atomic
    def update_note(
        cls,
        note: VideoNote,
        **kwargs,
    ) -> VideoNote:
        """
        Notu güncelle.
        """
        allowed_fields = [
            'content_text', 'visibility', 'color', 'tags', 'is_pinned'
        ]
        
        for field in allowed_fields:
            if field in kwargs:
                setattr(note, field, kwargs[field])
        
        note.save()
        return note
    
    @classmethod
    @transaction.atomic
    def delete_note(cls, note: VideoNote) -> None:
        """
        Notu sil.
        """
        note_id = note.id
        note.delete()
        logger.info(f"Note deleted: note={note_id}")
    
    @classmethod
    def get_user_notes(
        cls,
        user,
        content: CourseContent = None,
        course: Course = None,
        note_type: str = None,
        include_public: bool = False,
    ) -> List[VideoNote]:
        """
        Kullanıcının notlarını getir.
        """
        queryset = VideoNote.objects.filter(user=user)
        
        if content:
            queryset = queryset.filter(content=content)
        elif course:
            queryset = queryset.filter(course=course)
        
        if note_type:
            queryset = queryset.filter(note_type=note_type)
        
        if include_public:
            # Kullanıcının kendi notları + public notlar
            public_notes = VideoNote.objects.filter(
                content=content,
                visibility=VideoNote.NoteVisibility.PUBLIC,
            ).exclude(user=user)
            queryset = queryset | public_notes
        
        return list(queryset.order_by('video_ts', '-created_at'))
    
    @classmethod
    def get_public_notes(
        cls,
        content: CourseContent,
        exclude_user=None,
    ) -> List[VideoNote]:
        """
        İçerik için public notları getir.
        """
        queryset = VideoNote.objects.filter(
            content=content,
            visibility__in=[
                VideoNote.NoteVisibility.PUBLIC,
                VideoNote.NoteVisibility.GROUP,
            ],
        ).select_related('user')
        
        if exclude_user:
            queryset = queryset.exclude(user=exclude_user)
        
        return list(queryset.order_by('video_ts', '-like_count'))
    
    # ======== Thread Yönetimi ========
    
    @classmethod
    @transaction.atomic
    def add_reply(
        cls,
        user,
        note: VideoNote,
        content_text: str,
        parent: NoteReply = None,
    ) -> NoteReply:
        """
        Nota cevap ekle.
        """
        reply = NoteReply.objects.create(
            tenant=user.tenant,
            note=note,
            user=user,
            parent=parent,
            content_text=content_text,
        )
        
        # Sayacı güncelle
        VideoNote.objects.filter(id=note.id).update(
            reply_count=F('reply_count') + 1
        )
        
        return reply
    
    @classmethod
    def get_replies(cls, note: VideoNote) -> List[NoteReply]:
        """
        Not için cevapları getir.
        """
        return list(
            NoteReply.objects.filter(note=note, parent__isnull=True)
            .select_related('user')
            .prefetch_related('children')
            .order_by('created_at')
        )
    
    @classmethod
    @transaction.atomic
    def delete_reply(cls, reply: NoteReply) -> None:
        """
        Cevabı sil.
        """
        note = reply.note
        reply.delete()
        
        # Sayacı güncelle
        VideoNote.objects.filter(id=note.id).update(
            reply_count=F('reply_count') - 1
        )
    
    # ======== Reaksiyon Yönetimi ========
    
    @classmethod
    @transaction.atomic
    def toggle_reaction(
        cls,
        user,
        reaction_type: str,
        note: VideoNote = None,
        reply: NoteReply = None,
    ) -> tuple:
        """
        Reaksiyon ekle/kaldır.
        
        Returns:
            (added: bool, reaction: NoteReaction or None)
        """
        if not note and not reply:
            raise ValueError("note or reply required")
        
        filters = {
            'user': user,
            'reaction_type': reaction_type,
        }
        
        if note:
            filters['note'] = note
        else:
            filters['reply'] = reply
        
        existing = NoteReaction.objects.filter(**filters).first()
        
        if existing:
            existing.delete()
            
            # Sayacı güncelle
            if note and reaction_type == NoteReaction.ReactionType.LIKE:
                VideoNote.objects.filter(id=note.id).update(
                    like_count=F('like_count') - 1
                )
            elif reply and reaction_type == NoteReaction.ReactionType.LIKE:
                NoteReply.objects.filter(id=reply.id).update(
                    like_count=F('like_count') - 1
                )
            
            return False, None
        else:
            reaction = NoteReaction.objects.create(
                tenant=user.tenant,
                user=user,
                note=note,
                reply=reply,
                reaction_type=reaction_type,
            )
            
            # Sayacı güncelle
            if note and reaction_type == NoteReaction.ReactionType.LIKE:
                VideoNote.objects.filter(id=note.id).update(
                    like_count=F('like_count') + 1
                )
            elif reply and reaction_type == NoteReaction.ReactionType.LIKE:
                NoteReply.objects.filter(id=reply.id).update(
                    like_count=F('like_count') + 1
                )
            
            return True, reaction
    
    # ======== Paylaşım ========
    
    @classmethod
    @transaction.atomic
    def share_note(
        cls,
        note: VideoNote,
        visibility: str,
    ) -> VideoNote:
        """
        Notu paylaş.
        """
        note.visibility = visibility
        
        # Share token oluştur
        if not note.share_token:
            note.share_token = secrets.token_urlsafe(32)
        
        note.save()
        return note
    
    @classmethod
    def get_by_share_token(cls, token: str) -> Optional[VideoNote]:
        """
        Paylaşım tokeni ile notu getir.
        """
        return VideoNote.objects.filter(
            share_token=token,
            visibility__in=[
                VideoNote.NoteVisibility.GROUP,
                VideoNote.NoteVisibility.PUBLIC,
            ],
        ).first()
    
    # ======== Dışa Aktarma ========
    
    @classmethod
    @transaction.atomic
    def request_export(
        cls,
        user,
        format: str = NoteExport.ExportFormat.PDF,
        course: Course = None,
    ) -> NoteExport:
        """
        Not dışa aktarma talebi oluştur.
        """
        export = NoteExport.objects.create(
            tenant=user.tenant,
            user=user,
            course=course,
            format=format,
            status=NoteExport.ExportStatus.PENDING,
        )
        
        # TODO: Celery task ile async işle
        # export_notes_task.delay(export.id)
        
        logger.info(f"Note export requested: user={user.id}, export={export.id}")
        
        return export
    
    @classmethod
    def get_user_exports(cls, user) -> List[NoteExport]:
        """
        Kullanıcının export'larını getir.
        """
        return list(
            NoteExport.objects.filter(user=user)
            .order_by('-created_at')[:10]
        )
    
    # ======== Bookmarks ========
    
    @classmethod
    def get_user_bookmarks(cls, user, course: Course = None) -> List[VideoNote]:
        """
        Kullanıcının yer işaretlerini getir.
        """
        queryset = VideoNote.objects.filter(
            user=user,
            note_type=VideoNote.NoteType.BOOKMARK,
        )
        
        if course:
            queryset = queryset.filter(course=course)
        
        return list(queryset.order_by('-created_at'))
    
    @classmethod
    @transaction.atomic
    def quick_bookmark(
        cls,
        user,
        content: CourseContent,
        video_ts: int,
    ) -> VideoNote:
        """
        Hızlı yer işareti ekle.
        """
        return cls.create_note(
            user=user,
            course=content.module.course,
            content=content,
            note_type=VideoNote.NoteType.BOOKMARK,
            video_ts=video_ts,
        )

