# Generated migration for certificates app

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid
import backend.certificates.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tenants', '0001_initial'),
        ('courses', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CertificateTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Şablon Adı')),
                ('description', models.TextField(blank=True, verbose_name='Açıklama')),
                ('background_image', models.ImageField(blank=True, help_text='Sertifika arka plan görseli (opsiyonel)', null=True, upload_to='certificate_templates/', verbose_name='Arka Plan Görseli')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='certificate_templates/', verbose_name='Logo')),
                ('style_config', models.JSONField(blank=True, default=dict, help_text='CSS ve düzen ayarları', verbose_name='Stil Ayarları')),
                ('html_template', models.TextField(blank=True, help_text='Jinja2 şablon sözdizimi kullanılır', verbose_name='HTML Şablonu')),
                ('is_default', models.BooleanField(default=False, verbose_name='Varsayılan')),
                ('is_active', models.BooleanField(default=True, verbose_name='Aktif')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificate_templates', to='tenants.tenant', verbose_name='Tenant')),
            ],
            options={
                'verbose_name': 'Sertifika Şablonu',
                'verbose_name_plural': 'Sertifika Şablonları',
                'ordering': ['-is_default', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Certificate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('verification_code', models.CharField(editable=False, max_length=32, unique=True, verbose_name='Doğrulama Kodu')),
                ('title', models.CharField(max_length=200, verbose_name='Sertifika Başlığı')),
                ('description', models.TextField(blank=True, verbose_name='Açıklama')),
                ('completion_date', models.DateField(verbose_name='Tamamlama Tarihi')),
                ('completion_percent', models.PositiveIntegerField(default=100, verbose_name='Tamamlama Yüzdesi')),
                ('final_score', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, verbose_name='Final Notu')),
                ('skills', models.JSONField(blank=True, default=list, verbose_name='Kazanılan Beceriler')),
                ('total_hours', models.DecimalField(decimal_places=1, default=0, max_digits=6, verbose_name='Toplam Süre (saat)')),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to=backend.certificates.models.certificate_upload_path, verbose_name='PDF Dosyası')),
                ('status', models.CharField(choices=[('pending', 'Beklemede'), ('generated', 'Oluşturuldu'), ('issued', 'Verildi'), ('revoked', 'İptal Edildi')], db_index=True, default='pending', max_length=20, verbose_name='Durum')),
                ('digital_signature', models.TextField(blank=True, verbose_name='Dijital İmza')),
                ('is_public', models.BooleanField(default=True, verbose_name='Herkese Açık')),
                ('share_url', models.CharField(blank=True, max_length=255, verbose_name='Paylaşım Linki')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Ek Veri')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('issued_at', models.DateTimeField(blank=True, null=True, verbose_name='Verilme Tarihi')),
                ('revoked_at', models.DateTimeField(blank=True, null=True, verbose_name='İptal Tarihi')),
                ('course', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='courses.course', verbose_name='Kurs')),
                ('enrollment', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='certificate', to='courses.enrollment', verbose_name='Kayıt')),
                ('issued_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='issued_certificates', to=settings.AUTH_USER_MODEL, verbose_name='Veren')),
                ('template', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='certificates', to='certificates.certificatetemplate', verbose_name='Şablon')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to='tenants.tenant', verbose_name='Tenant')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='certificates', to=settings.AUTH_USER_MODEL, verbose_name='Kullanıcı')),
            ],
            options={
                'verbose_name': 'Sertifika',
                'verbose_name_plural': 'Sertifikalar',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CertificateDownload',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP Adresi')),
                ('user_agent', models.CharField(blank=True, max_length=500, verbose_name='User Agent')),
                ('downloaded_at', models.DateTimeField(auto_now_add=True)),
                ('certificate', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='downloads', to='certificates.certificate')),
                ('downloaded_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Sertifika İndirme',
                'verbose_name_plural': 'Sertifika İndirmeleri',
                'ordering': ['-downloaded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['verification_code'], name='certificate_verific_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['user', 'status'], name='certificate_user_st_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='certificate',
            index=models.Index(fields=['course', 'status'], name='certificate_course_g7h8i9_idx'),
        ),
    ]

