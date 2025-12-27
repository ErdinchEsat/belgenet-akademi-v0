"""
Live Session Model Tests
========================

Model testleri.
"""

from datetime import timedelta
from django.test import TestCase
from django.utils import timezone

from backend.live.models import (
    LiveSession,
    LiveSessionParticipant,
    LiveSessionAttendanceSummary,
    LiveSessionRecording,
    LiveSessionPolicy,
    LiveProviderConfig,
)


class LiveSessionModelTest(TestCase):
    """LiveSession model testleri."""
    
    @classmethod
    def setUpTestData(cls):
        """Test verilerini oluştur."""
        from backend.tenants.models import Tenant
        from backend.courses.models import Course
        from backend.users.models import User
        
        # Tenant
        cls.tenant = Tenant.objects.create(
            name='Test Akademi',
            slug='test-akademi',
        )
        
        # User
        cls.user = User.objects.create_user(
            email='instructor@test.com',
            password='testpass123',
            first_name='Test',
            last_name='Instructor',
            tenant=cls.tenant,
            role='INSTRUCTOR',
        )
        
        # Course
        cls.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            description='Test course description',
            category='Technology',
            tenant=cls.tenant,
        )
        cls.course.instructors.add(cls.user)
    
    def test_create_session(self):
        """Session oluşturma testi."""
        now = timezone.now()
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            scheduled_start=now + timedelta(hours=1),
            scheduled_end=now + timedelta(hours=2),
            provider='jitsi',
        )
        
        self.assertIsNotNone(session.id)
        self.assertIsNotNone(session.room_id)
        self.assertEqual(session.status, LiveSession.Status.DRAFT)
        self.assertEqual(session.type, LiveSession.Type.SCHEDULED)
    
    def test_session_room_id_auto_generated(self):
        """Room ID otomatik oluşturma testi."""
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            scheduled_start=timezone.now() + timedelta(hours=1),
            scheduled_end=timezone.now() + timedelta(hours=2),
            provider='jitsi',
        )
        
        self.assertTrue(session.room_id.startswith('test-akademi-'))
    
    def test_session_start(self):
        """Session başlatma testi."""
        now = timezone.now()
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            status=LiveSession.Status.SCHEDULED,
            scheduled_start=now,
            scheduled_end=now + timedelta(hours=1),
            provider='jitsi',
        )
        
        session.start()
        session.refresh_from_db()
        
        self.assertEqual(session.status, LiveSession.Status.LIVE)
        self.assertIsNotNone(session.actual_start)
    
    def test_session_end(self):
        """Session sonlandırma testi."""
        now = timezone.now()
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            status=LiveSession.Status.LIVE,
            scheduled_start=now - timedelta(hours=1),
            scheduled_end=now,
            actual_start=now - timedelta(hours=1),
            provider='jitsi',
        )
        
        session.end()
        session.refresh_from_db()
        
        self.assertEqual(session.status, LiveSession.Status.ENDED)
        self.assertIsNotNone(session.actual_end)
        self.assertGreater(session.total_duration_minutes, 0)
    
    def test_session_duration(self):
        """Süre hesaplama testi."""
        now = timezone.now()
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            scheduled_start=now,
            scheduled_end=now + timedelta(minutes=90),
            provider='jitsi',
        )
        
        self.assertEqual(session.duration_minutes, 90)
    
    def test_session_is_live(self):
        """is_live property testi."""
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            status=LiveSession.Status.LIVE,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=1),
            provider='jitsi',
        )
        
        self.assertTrue(session.is_live)
    
    def test_session_can_join(self):
        """can_join property testi."""
        session = LiveSession.objects.create(
            tenant=self.tenant,
            course=self.course,
            created_by=self.user,
            title='Test Session',
            status=LiveSession.Status.LIVE,
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=1),
            max_participants=100,
            participant_count=50,
            provider='jitsi',
        )
        
        self.assertTrue(session.can_join)
        
        # Kapasite dolu
        session.participant_count = 100
        session.save()
        
        self.assertFalse(session.can_join)


class LiveSessionParticipantModelTest(TestCase):
    """Katılımcı model testleri."""
    
    @classmethod
    def setUpTestData(cls):
        from backend.tenants.models import Tenant
        from backend.courses.models import Course
        from backend.users.models import User
        
        cls.tenant = Tenant.objects.create(name='Test', slug='test')
        cls.user = User.objects.create_user(
            email='student@test.com',
            password='test123',
            tenant=cls.tenant,
        )
        cls.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            description='Test',
            category='Tech',
            tenant=cls.tenant,
        )
        cls.session = LiveSession.objects.create(
            tenant=cls.tenant,
            course=cls.course,
            title='Test Session',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=1),
            provider='jitsi',
        )
    
    def test_create_participant(self):
        """Katılımcı oluşturma testi."""
        participant = LiveSessionParticipant.objects.create(
            session=self.session,
            user=self.user,
            role=LiveSessionParticipant.Role.PARTICIPANT,
            joined_at=timezone.now(),
        )
        
        self.assertIsNotNone(participant.id)
        self.assertTrue(participant.is_active)
    
    def test_participant_leave(self):
        """Ayrılma testi."""
        joined = timezone.now()
        participant = LiveSessionParticipant.objects.create(
            session=self.session,
            user=self.user,
            role=LiveSessionParticipant.Role.PARTICIPANT,
            joined_at=joined,
        )
        
        participant.leave()
        participant.refresh_from_db()
        
        self.assertFalse(participant.is_active)
        self.assertIsNotNone(participant.left_at)
        self.assertGreaterEqual(participant.duration_seconds, 0)


class LiveSessionPolicyModelTest(TestCase):
    """Politika model testleri."""
    
    @classmethod
    def setUpTestData(cls):
        from backend.tenants.models import Tenant
        from backend.courses.models import Course
        
        cls.tenant = Tenant.objects.create(name='Test', slug='test')
        cls.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            description='Test',
            category='Tech',
            tenant=cls.tenant,
        )
    
    def test_create_tenant_policy(self):
        """Tenant policy oluşturma testi."""
        policy = LiveSessionPolicy.objects.create(
            tenant=self.tenant,
            attendance_threshold_percent=80,
        )
        
        self.assertEqual(policy.attendance_threshold_percent, 80)
    
    def test_policy_validation(self):
        """Policy scope validasyonu."""
        from django.core.exceptions import ValidationError
        
        policy = LiveSessionPolicy(
            tenant=self.tenant,
            course=self.course,  # İkisi birden olamaz
        )
        
        with self.assertRaises(ValidationError):
            policy.clean()


class LiveSessionRecordingModelTest(TestCase):
    """Recording model testleri."""
    
    @classmethod
    def setUpTestData(cls):
        from backend.tenants.models import Tenant
        from backend.courses.models import Course
        
        cls.tenant = Tenant.objects.create(name='Test', slug='test')
        cls.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            description='Test',
            category='Tech',
            tenant=cls.tenant,
        )
        cls.session = LiveSession.objects.create(
            tenant=cls.tenant,
            course=cls.course,
            title='Test Session',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=1),
            provider='jitsi',
        )
    
    def test_create_recording(self):
        """Kayıt oluşturma testi."""
        recording = LiveSessionRecording.objects.create(
            tenant=self.tenant,
            session=self.session,
            provider_recording_id='test-recording-123',
            duration_seconds=3600,
            file_size_bytes=1024 * 1024 * 500,  # 500 MB
        )
        
        self.assertEqual(recording.status, LiveSessionRecording.Status.PROCESSING)
        self.assertEqual(recording.duration_minutes, 60)
        self.assertEqual(recording.file_size_mb, 500.0)
    
    def test_recording_publish(self):
        """Yayınlama testi."""
        recording = LiveSessionRecording.objects.create(
            tenant=self.tenant,
            session=self.session,
            provider_recording_id='test-recording-123',
            status=LiveSessionRecording.Status.READY,
        )
        
        recording.publish()
        recording.refresh_from_db()
        
        self.assertEqual(recording.status, LiveSessionRecording.Status.PUBLISHED)
        self.assertIsNotNone(recording.published_at)
    
    def test_recording_unpublish(self):
        """Yayından kaldırma testi."""
        recording = LiveSessionRecording.objects.create(
            tenant=self.tenant,
            session=self.session,
            provider_recording_id='test-recording-123',
            status=LiveSessionRecording.Status.PUBLISHED,
            published_at=timezone.now(),
        )
        
        recording.unpublish()
        recording.refresh_from_db()
        
        self.assertEqual(recording.status, LiveSessionRecording.Status.READY)
        self.assertIsNone(recording.published_at)

