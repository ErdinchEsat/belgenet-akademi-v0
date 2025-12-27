# Generated migration for storage app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import backend.storage.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileUpload',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('file', models.FileField(max_length=500, upload_to=backend.storage.models.upload_to_path, verbose_name='Dosya')),
                ('original_filename', models.CharField(max_length=255, verbose_name='Orijinal Dosya Adı')),
                ('category', models.CharField(choices=[('profile', 'Profil Resmi'), ('assignment', 'Ödev Dosyası'), ('submission', 'Ödev Teslimi'), ('material', 'Kurs Materyali'), ('certificate', 'Sertifika'), ('document', 'Döküman'), ('attachment', 'Ek Dosya'), ('other', 'Diğer')], db_index=True, default='other', max_length=20, verbose_name='Kategori')),
                ('mime_type', models.CharField(blank=True, max_length=100, verbose_name='MIME Tipi')),
                ('file_size', models.PositiveBigIntegerField(default=0, verbose_name='Dosya Boyutu (byte)')),
                ('file_hash', models.CharField(blank=True, help_text='SHA-256 hash değeri', max_length=64, verbose_name='Dosya Hash')),
                ('status', models.CharField(choices=[('pending', 'Beklemede'), ('processing', 'İşleniyor'), ('completed', 'Tamamlandı'), ('failed', 'Başarısız'), ('deleted', 'Silindi')], db_index=True, default='pending', max_length=20, verbose_name='Durum')),
                ('error_message', models.TextField(blank=True, verbose_name='Hata Mesajı')),
                ('content_type', models.CharField(blank=True, help_text='İlişkili model tipi (örn: courses.Course)', max_length=100, verbose_name='İçerik Tipi')),
                ('object_id', models.CharField(blank=True, help_text='İlişkili nesne ID', max_length=50, verbose_name='Nesne ID')),
                ('width', models.PositiveIntegerField(blank=True, null=True, verbose_name='Genişlik')),
                ('height', models.PositiveIntegerField(blank=True, null=True, verbose_name='Yükseklik')),
                ('is_public', models.BooleanField(default=False, verbose_name='Herkese Açık')),
                ('access_count', models.PositiveIntegerField(default=0, verbose_name='Erişim Sayısı')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Ek Veri')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Son Kullanma Tarihi')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='tenants.tenant', verbose_name='Tenant')),
                ('uploaded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='uploaded_files', to=settings.AUTH_USER_MODEL, verbose_name='Yükleyen')),
            ],
            options={
                'verbose_name': 'Dosya',
                'verbose_name_plural': 'Dosyalar',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UploadSession',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('filename', models.CharField(max_length=255, verbose_name='Dosya Adı')),
                ('file_size', models.PositiveBigIntegerField(verbose_name='Toplam Boyut')),
                ('chunk_size', models.PositiveIntegerField(default=5242880, verbose_name='Parça Boyutu')),
                ('total_chunks', models.PositiveIntegerField(verbose_name='Toplam Parça')),
                ('uploaded_chunks', models.PositiveIntegerField(default=0, verbose_name='Yüklenen Parça')),
                ('is_completed', models.BooleanField(default=False, verbose_name='Tamamlandı')),
                ('category', models.CharField(choices=[('profile', 'Profil Resmi'), ('assignment', 'Ödev Dosyası'), ('submission', 'Ödev Teslimi'), ('material', 'Kurs Materyali'), ('certificate', 'Sertifika'), ('document', 'Döküman'), ('attachment', 'Ek Dosya'), ('other', 'Diğer')], default='other', max_length=20)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('completed_file', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='upload_sessions', to='storage.fileupload')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='upload_sessions', to='tenants.tenant')),
                ('uploaded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='upload_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Yükleme Oturumu',
                'verbose_name_plural': 'Yükleme Oturumları',
            },
        ),
        migrations.CreateModel(
            name='ImageVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(choices=[('thumbnail', 'Küçük (150x150)'), ('small', 'Küçük (300x300)'), ('medium', 'Orta (600x600)'), ('large', 'Büyük (1200x1200)'), ('original', 'Orijinal')], max_length=20, verbose_name='Boyut')),
                ('file', models.ImageField(max_length=500, upload_to='variants/', verbose_name='Dosya')),
                ('width', models.PositiveIntegerField(verbose_name='Genişlik')),
                ('height', models.PositiveIntegerField(verbose_name='Yükseklik')),
                ('file_size', models.PositiveIntegerField(verbose_name='Dosya Boyutu')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('original', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='storage.fileupload', verbose_name='Orijinal')),
            ],
            options={
                'verbose_name': 'Görsel Varyantı',
                'verbose_name_plural': 'Görsel Varyantları',
                'unique_together': {('original', 'size')},
            },
        ),
        migrations.AddIndex(
            model_name='fileupload',
            index=models.Index(fields=['category', 'status'], name='storage_fil_categor_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='fileupload',
            index=models.Index(fields=['uploaded_by', 'category'], name='storage_fil_uploade_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='fileupload',
            index=models.Index(fields=['content_type', 'object_id'], name='storage_fil_content_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='fileupload',
            index=models.Index(fields=['file_hash'], name='storage_fil_file_ha_j0k1l2_idx'),
        ),
    ]

