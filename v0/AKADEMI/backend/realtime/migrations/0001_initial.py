# Generated migration for realtime app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0001_initial'),
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(blank=True, help_text='Grup konuşmaları için', max_length=100, verbose_name='Konuşma Adı')),
                ('type', models.CharField(choices=[('private', 'Özel'), ('group', 'Grup'), ('class', 'Sınıf'), ('course', 'Kurs'), ('support', 'Destek')], default='private', max_length=20, verbose_name='Tür')),
                ('avatar', models.URLField(blank=True, verbose_name='Grup Görseli')),
                ('description', models.TextField(blank=True, verbose_name='Açıklama')),
                ('related_type', models.CharField(blank=True, max_length=50, verbose_name='İlişkili Tür')),
                ('related_id', models.CharField(blank=True, max_length=50, verbose_name='İlişkili ID')),
                ('is_muted', models.BooleanField(default=False, verbose_name='Sessiz')),
                ('is_archived', models.BooleanField(default=False, verbose_name='Arşivlenmiş')),
                ('last_message_at', models.DateTimeField(blank=True, null=True, verbose_name='Son Mesaj Zamanı')),
                ('last_message_preview', models.CharField(blank=True, max_length=100, verbose_name='Son Mesaj Önizleme')),
                ('message_count', models.PositiveIntegerField(default=0, verbose_name='Mesaj Sayısı')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversations', to='tenants.tenant', verbose_name='Tenant')),
            ],
            options={
                'verbose_name': 'Konuşma',
                'verbose_name_plural': 'Konuşmalar',
                'ordering': ['-last_message_at', '-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ConversationParticipant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(choices=[('member', 'Üye'), ('admin', 'Yönetici'), ('owner', 'Sahip')], default='member', max_length=20, verbose_name='Rol')),
                ('is_muted', models.BooleanField(default=False, verbose_name='Sessiz')),
                ('muted_until', models.DateTimeField(blank=True, null=True, verbose_name='Sessiz Bitiş')),
                ('last_read_at', models.DateTimeField(blank=True, null=True, verbose_name='Son Okuma')),
                ('unread_count', models.PositiveIntegerField(default=0, verbose_name='Okunmamış')),
                ('is_pinned', models.BooleanField(default=False, verbose_name='Sabitlenmiş')),
                ('joined_at', models.DateTimeField(auto_now_add=True)),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_participants', to='realtime.conversation')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conversation_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Konuşma Katılımcısı',
                'verbose_name_plural': 'Konuşma Katılımcıları',
                'unique_together': {('conversation', 'user')},
            },
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('type', models.CharField(choices=[('text', 'Metin'), ('image', 'Görsel'), ('file', 'Dosya'), ('audio', 'Ses'), ('video', 'Video'), ('system', 'Sistem'), ('reply', 'Yanıt')], default='text', max_length=20, verbose_name='Tür')),
                ('content', models.TextField(verbose_name='İçerik')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Ek Veri')),
                ('is_edited', models.BooleanField(default=False, verbose_name='Düzenlendi')),
                ('edited_at', models.DateTimeField(blank=True, null=True, verbose_name='Düzenleme Zamanı')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Silindi')),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Silinme Zamanı')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('attachment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_messages', to='storage.fileupload')),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='realtime.conversation')),
                ('reply_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='replies', to='realtime.chatmessage')),
                ('sender', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='chat_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sohbet Mesajı',
                'verbose_name_plural': 'Sohbet Mesajları',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='MessageReadStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('read_at', models.DateTimeField(auto_now_add=True)),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='read_statuses', to='realtime.chatmessage')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='message_read_statuses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Mesaj Okunma Durumu',
                'verbose_name_plural': 'Mesaj Okunma Durumları',
                'unique_together': {('message', 'user')},
            },
        ),
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=True, verbose_name='E-posta Bildirimleri')),
                ('push_enabled', models.BooleanField(default=True, verbose_name='Push Bildirimleri')),
                ('sms_enabled', models.BooleanField(default=False, verbose_name='SMS Bildirimleri')),
                ('notify_assignments', models.BooleanField(default=True, verbose_name='Ödev Bildirimleri')),
                ('notify_grades', models.BooleanField(default=True, verbose_name='Not Bildirimleri')),
                ('notify_messages', models.BooleanField(default=True, verbose_name='Mesaj Bildirimleri')),
                ('notify_live_sessions', models.BooleanField(default=True, verbose_name='Canlı Ders Bildirimleri')),
                ('notify_announcements', models.BooleanField(default=True, verbose_name='Duyuru Bildirimleri')),
                ('notify_system', models.BooleanField(default=True, verbose_name='Sistem Bildirimleri')),
                ('quiet_hours_enabled', models.BooleanField(default=False, verbose_name='Sessiz Saatler Aktif')),
                ('quiet_hours_start', models.TimeField(blank=True, null=True, verbose_name='Sessiz Saat Başlangıç')),
                ('quiet_hours_end', models.TimeField(blank=True, null=True, verbose_name='Sessiz Saat Bitiş')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Bildirim Tercihi',
                'verbose_name_plural': 'Bildirim Tercihleri',
            },
        ),
        migrations.AddField(
            model_name='conversation',
            name='participants',
            field=models.ManyToManyField(related_name='conversations', through='realtime.ConversationParticipant', to=settings.AUTH_USER_MODEL, verbose_name='Katılımcılar'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['type', 'tenant'], name='realtime_co_type_te_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='conversation',
            index=models.Index(fields=['last_message_at'], name='realtime_co_last_me_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['conversation', 'created_at'], name='realtime_ch_convers_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['sender', 'created_at'], name='realtime_ch_sender_j0k1l2_idx'),
        ),
    ]

