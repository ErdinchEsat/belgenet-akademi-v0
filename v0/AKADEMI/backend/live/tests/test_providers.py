"""
Live Session Provider Tests
===========================

Provider adapter testleri.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from backend.live.models import LiveSession, LiveProviderConfig
from backend.live.providers.base import (
    LiveClassProvider,
    RoomInfo,
    JoinInfo,
    NormalizedEvent,
)
from backend.live.providers.jitsi import JitsiProvider


class JitsiProviderTest(TestCase):
    """Jitsi provider testleri."""
    
    @classmethod
    def setUpTestData(cls):
        from backend.tenants.models import Tenant
        from backend.courses.models import Course
        from backend.users.models import User
        
        cls.tenant = Tenant.objects.create(name='Test', slug='test')
        cls.user = User.objects.create_user(
            email='instructor@test.com',
            password='test123',
            first_name='Test',
            last_name='User',
            tenant=cls.tenant,
        )
        cls.course = Course.objects.create(
            title='Test Course',
            slug='test-course',
            description='Test',
            category='Tech',
            tenant=cls.tenant,
        )
        
        cls.config = LiveProviderConfig.objects.create(
            tenant=cls.tenant,
            provider='jitsi',
            is_active=True,
            is_default=True,
            jitsi_domain='meet.example.com',
            jitsi_app_id='test-app',
            jitsi_jwt_secret='test-secret-key-12345',
        )
        
        cls.session = LiveSession.objects.create(
            tenant=cls.tenant,
            course=cls.course,
            created_by=cls.user,
            title='Test Session',
            scheduled_start=timezone.now(),
            scheduled_end=timezone.now() + timedelta(hours=1),
            provider='jitsi',
        )
    
    def test_provider_initialization(self):
        """Provider başlatma testi."""
        provider = JitsiProvider(self.config)
        
        self.assertEqual(provider.domain, 'meet.example.com')
        self.assertEqual(provider.app_id, 'test-app')
    
    def test_create_room(self):
        """Oda oluşturma testi."""
        provider = JitsiProvider(self.config)
        room_info = provider.create_room(self.session)
        
        self.assertIsInstance(room_info, RoomInfo)
        self.assertEqual(room_info.room_id, self.session.room_id)
        self.assertTrue(room_info.room_url.startswith('https://meet.example.com/'))
    
    def test_generate_join_url_moderator(self):
        """Moderatör join URL testi."""
        provider = JitsiProvider(self.config)
        join_info = provider.generate_join_url(self.session, self.user, 'host')
        
        self.assertIsInstance(join_info, JoinInfo)
        self.assertIn('jwt=', join_info.join_url)
        self.assertIsNotNone(join_info.token)
        self.assertEqual(join_info.role, 'host')
        self.assertTrue(join_info.metadata.get('moderator'))
    
    def test_generate_join_url_participant(self):
        """Katılımcı join URL testi."""
        provider = JitsiProvider(self.config)
        join_info = provider.generate_join_url(self.session, self.user, 'participant')
        
        self.assertEqual(join_info.role, 'participant')
        self.assertFalse(join_info.metadata.get('moderator'))
    
    def test_jwt_token_contains_user_info(self):
        """JWT token kullanıcı bilgisi testi."""
        import jwt
        
        provider = JitsiProvider(self.config)
        join_info = provider.generate_join_url(self.session, self.user, 'host')
        
        # Token'ı decode et
        decoded = jwt.decode(join_info.token, self.config.jitsi_jwt_secret, algorithms=['HS256'])
        
        self.assertEqual(decoded['context']['user']['id'], str(self.user.id))
        self.assertEqual(decoded['context']['user']['email'], self.user.email)
        self.assertTrue(decoded['moderator'])
    
    def test_jwt_token_expiry(self):
        """JWT token expiry testi."""
        import jwt
        
        provider = JitsiProvider(self.config)
        join_info = provider.generate_join_url(self.session, self.user, 'host')
        
        decoded = jwt.decode(join_info.token, self.config.jitsi_jwt_secret, algorithms=['HS256'])
        
        # Token 5 dakika içinde expire olmalı
        now = int(time.time())
        self.assertGreater(decoded['exp'], now)
        self.assertLess(decoded['exp'], now + 600)  # 10 dakikadan az
    
    def test_handle_webhook_participant_joined(self):
        """Webhook participant joined testi."""
        provider = JitsiProvider(self.config)
        
        payload = {
            'event': 'participant_joined',
            'room': self.session.room_id,
            'participant': {
                'id': str(self.user.id),
                'name': self.user.full_name,
            },
            'timestamp': time.time(),
        }
        
        event = provider.handle_webhook(payload)
        
        self.assertIsInstance(event, NormalizedEvent)
        self.assertEqual(event.event_type, NormalizedEvent.PARTICIPANT_JOINED)
        self.assertEqual(event.session_id, self.session.room_id)
        self.assertEqual(event.provider, 'jitsi')
    
    def test_handle_webhook_session_ended(self):
        """Webhook session ended testi."""
        provider = JitsiProvider(self.config)
        
        payload = {
            'event': 'room_destroyed',
            'room': self.session.room_id,
            'timestamp': time.time(),
        }
        
        event = provider.handle_webhook(payload)
        
        self.assertEqual(event.event_type, NormalizedEvent.SESSION_ENDED)
    
    @patch('backend.live.providers.jitsi.requests')
    def test_health_check_success(self, mock_requests):
        """Health check başarılı testi."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.get.return_value = mock_response
        
        provider = JitsiProvider(self.config)
        result = provider.health_check()
        
        self.assertTrue(result)
        mock_requests.get.assert_called_once()
    
    @patch('backend.live.providers.jitsi.requests')
    def test_health_check_failure(self, mock_requests):
        """Health check başarısız testi."""
        mock_requests.get.side_effect = Exception("Connection error")
        
        provider = JitsiProvider(self.config)
        result = provider.health_check()
        
        self.assertFalse(result)


class ProviderFactoryTest(TestCase):
    """Provider factory testleri."""
    
    @classmethod
    def setUpTestData(cls):
        from backend.tenants.models import Tenant
        
        cls.tenant = Tenant.objects.create(name='Test', slug='test')
        
        cls.config = LiveProviderConfig.objects.create(
            tenant=cls.tenant,
            provider='jitsi',
            is_active=True,
            is_default=True,
            jitsi_domain='meet.example.com',
            jitsi_app_id='test-app',
            jitsi_jwt_secret='test-secret',
        )
    
    def test_get_provider_returns_correct_type(self):
        """Doğru provider tipi döner."""
        from backend.live.providers import get_provider
        
        provider = get_provider(self.tenant)
        
        self.assertIsInstance(provider, JitsiProvider)
    
    def test_get_provider_no_config_raises_error(self):
        """Config yoksa hata fırlatır."""
        from backend.tenants.models import Tenant
        from backend.live.providers import get_provider
        
        empty_tenant = Tenant.objects.create(name='Empty', slug='empty')
        
        with self.assertRaises(ValueError):
            get_provider(empty_tenant)
    
    def test_get_provider_inactive_config_raises_error(self):
        """Inactive config için hata fırlatır."""
        from backend.tenants.models import Tenant
        from backend.live.providers import get_provider
        
        tenant = Tenant.objects.create(name='Inactive', slug='inactive')
        LiveProviderConfig.objects.create(
            tenant=tenant,
            provider='jitsi',
            is_active=False,
            jitsi_domain='meet.example.com',
            jitsi_app_id='test',
            jitsi_jwt_secret='secret',
        )
        
        with self.assertRaises(ValueError):
            get_provider(tenant)


class NormalizedEventTest(TestCase):
    """Normalized event testleri."""
    
    def test_event_types_defined(self):
        """Event tipleri tanımlı."""
        self.assertEqual(NormalizedEvent.SESSION_STARTED, 'session_started')
        self.assertEqual(NormalizedEvent.PARTICIPANT_JOINED, 'participant_joined')
        self.assertEqual(NormalizedEvent.RECORDING_READY, 'recording_ready')
    
    def test_event_creation(self):
        """Event oluşturma."""
        event = NormalizedEvent(
            event_type=NormalizedEvent.SESSION_STARTED,
            session_id='test-room',
            timestamp=datetime.now(),
            payload={'test': 'data'},
            provider='jitsi',
        )
        
        self.assertEqual(event.event_type, 'session_started')
        self.assertEqual(event.provider, 'jitsi')

