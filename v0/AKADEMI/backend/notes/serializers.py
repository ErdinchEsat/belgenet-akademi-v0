"""
Notes Serializers
=================

Notes API serializer'ları.
"""

from rest_framework import serializers

from .models import VideoNote, NoteReply, NoteReaction, NoteExport


class NoteCreateSerializer(serializers.Serializer):
    """Not oluşturma request serializer."""
    
    note_type = serializers.ChoiceField(
        choices=VideoNote.NoteType.choices,
        default=VideoNote.NoteType.NOTE,
    )
    
    content_text = serializers.CharField(
        max_length=10000,
        allow_blank=True,
    )
    
    video_ts = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    
    video_ts_end = serializers.IntegerField(
        min_value=0,
        required=False,
        allow_null=True,
    )
    
    visibility = serializers.ChoiceField(
        choices=VideoNote.NoteVisibility.choices,
        default=VideoNote.NoteVisibility.PRIVATE,
    )
    
    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
    )
    
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list,
    )
    
    session_id = serializers.UUIDField(
        required=False,
        allow_null=True,
    )


class NoteUpdateSerializer(serializers.Serializer):
    """Not güncelleme request serializer."""
    
    content_text = serializers.CharField(
        max_length=10000,
        required=False,
    )
    
    visibility = serializers.ChoiceField(
        choices=VideoNote.NoteVisibility.choices,
        required=False,
    )
    
    color = serializers.CharField(
        max_length=20,
        required=False,
        allow_null=True,
    )
    
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )
    
    is_pinned = serializers.BooleanField(required=False)


class NoteResponseSerializer(serializers.ModelSerializer):
    """Not response serializer."""
    
    user_name = serializers.SerializerMethodField()
    time_display = serializers.CharField(read_only=True)
    user_reaction = serializers.SerializerMethodField()
    
    class Meta:
        model = VideoNote
        fields = [
            'id',
            'note_type',
            'content_text',
            'video_ts',
            'video_ts_end',
            'time_display',
            'visibility',
            'color',
            'tags',
            'is_pinned',
            'reply_count',
            'like_count',
            'user_name',
            'user_reaction',
            'share_token',
            'created_at',
            'updated_at',
        ]
    
    def get_user_name(self, obj):
        """Kullanıcı adını döndür."""
        if obj.visibility == VideoNote.NoteVisibility.PRIVATE:
            return None
        return obj.user.full_name or obj.user.email
    
    def get_user_reaction(self, obj):
        """Mevcut kullanıcının reaksiyonunu döndür."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        reaction = obj.reactions.filter(user=request.user).first()
        return reaction.reaction_type if reaction else None


class NoteListSerializer(serializers.ModelSerializer):
    """Not liste serializer (kısa versiyon)."""
    
    time_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = VideoNote
        fields = [
            'id',
            'note_type',
            'content_text',
            'video_ts',
            'time_display',
            'visibility',
            'is_pinned',
            'reply_count',
            'like_count',
            'created_at',
        ]


class ReplyCreateSerializer(serializers.Serializer):
    """Cevap oluşturma request serializer."""
    
    content_text = serializers.CharField(max_length=5000)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class ReplyResponseSerializer(serializers.ModelSerializer):
    """Cevap response serializer."""
    
    user_name = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = NoteReply
        fields = [
            'id',
            'content_text',
            'user_name',
            'like_count',
            'parent',
            'children',
            'created_at',
        ]
    
    def get_user_name(self, obj):
        return obj.user.full_name or obj.user.email
    
    def get_children(self, obj):
        """Nested cevapları döndür."""
        children = obj.children.all()[:5]  # Max 5 child
        return ReplyResponseSerializer(children, many=True).data


class ReactionSerializer(serializers.Serializer):
    """Reaksiyon request serializer."""
    
    reaction_type = serializers.ChoiceField(
        choices=NoteReaction.ReactionType.choices,
    )


class NotesExportSerializer(serializers.Serializer):
    """Not dışa aktarma request serializer."""
    
    format = serializers.ChoiceField(
        choices=NoteExport.ExportFormat.choices,
        default=NoteExport.ExportFormat.PDF,
    )
    
    course_id = serializers.IntegerField(required=False, allow_null=True)


class NotesExportResponseSerializer(serializers.ModelSerializer):
    """Not dışa aktarma response serializer."""
    
    class Meta:
        model = NoteExport
        fields = [
            'id',
            'format',
            'status',
            'file_url',
            'error_message',
            'created_at',
            'completed_at',
        ]


class NoteShareSerializer(serializers.Serializer):
    """Not paylaşım serializer."""
    
    visibility = serializers.ChoiceField(
        choices=[
            VideoNote.NoteVisibility.GROUP,
            VideoNote.NoteVisibility.PUBLIC,
        ],
    )

