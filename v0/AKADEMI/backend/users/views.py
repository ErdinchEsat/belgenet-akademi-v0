"""
User Views
==========

Kullanıcı API view'ları.
"""

from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .permissions import IsAdminOrSuperAdmin, IsOwnerOrAdmin, IsSuperAdmin
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom JWT Token view.
    Login endpoint - kullanıcı bilgilerini de döndürür.
    
    POST /api/v1/auth/token/
    """
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        
        # Başarılı login ise audit log oluştur
        if response.status_code == 200:
            try:
                from logs.audit.models import AuditLog
                from tools.logs.utils import get_client_ip
                from django.utils import timezone
                import logging
                
                audit_logger = logging.getLogger('backend.users')
                
                # Email'den user'ı al
                email = request.data.get('email')
                user = User.objects.get(email=email)
                
                # last_login güncelle
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Audit log oluştur
                ip = get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
                
                AuditLog.objects.create(
                    user=user,
                    username=user.email,  # Email'i username olarak kullan
                    action=AuditLog.ActionType.LOGIN,
                    object_repr=f"Kullanıcı girişi: {user.email}",
                    ip_address=ip,
                    user_agent=user_agent,
                    extra_data={
                        'email': user.email,
                        'user_id': str(user.id),
                        'role': user.role,
                    }
                )
                
                audit_logger.info(f"[AUDIT] Login: {user.email} from {ip}")
                
            except Exception as e:
                audit_logger.error(f"Error creating login audit log: {e}")
        
        return response


class RegisterView(generics.CreateAPIView):
    """
    Kullanıcı kayıt view.
    
    POST /api/v1/auth/register/
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            {
                'message': 'Kayıt başarılı. Lütfen e-posta adresinizi doğrulayın.',
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    """
    Mevcut kullanıcı bilgileri view.
    
    GET /api/v1/auth/me/
    PATCH /api/v1/auth/me/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """
    Şifre değiştirme view.
    
    POST /api/v1/auth/password/change/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        return Response({'message': 'Şifre başarıyla değiştirildi.'})


class LogoutView(APIView):
    """
    Logout view - JWT refresh token'ı blacklist'e ekler.
    
    POST /api/v1/auth/logout/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            from rest_framework_simplejwt.tokens import RefreshToken
            
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            return Response({'message': 'Başarıyla çıkış yapıldı.'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserViewSet(viewsets.ModelViewSet):
    """
    Kullanıcı CRUD ViewSet.
    
    GET /api/v1/users/           - Liste (Admin only)
    POST /api/v1/users/          - Oluştur (Admin only)
    GET /api/v1/users/{id}/      - Detay
    PATCH /api/v1/users/{id}/    - Güncelle
    DELETE /api/v1/users/{id}/   - Sil (Super Admin only)
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Kullanıcıları tenant bazlı filtrele.
        Super Admin tüm kullanıcıları görür.
        """
        user = self.request.user
        
        # Anonim kullanıcı kontrolü
        if not user.is_authenticated:
            return User.objects.none()
        
        if user.role == User.Role.SUPER_ADMIN:
            return User.objects.all()
        
        if user.role == User.Role.TENANT_ADMIN:
            return User.objects.filter(tenant=user.tenant)
        
        # Diğer kullanıcılar sadece kendilerini görebilir
        return User.objects.filter(id=user.id)

    def get_permissions(self):
        """
        Action bazlı permission.
        """
        if self.action in ['list', 'create']:
            return [IsAdminOrSuperAdmin()]
        if self.action == 'destroy':
            return [IsSuperAdmin()]
        return [IsOwnerOrAdmin()]

    def get_serializer_class(self):
        """
        Action bazlı serializer.
        """
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def students(self, request):
        """
        Öğrenci listesi.
        GET /api/v1/users/students/
        """
        queryset = self.get_queryset().filter(role=User.Role.STUDENT)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def instructors(self, request):
        """
        Eğitmen listesi.
        GET /api/v1/users/instructors/
        """
        queryset = self.get_queryset().filter(role=User.Role.INSTRUCTOR)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """
        Kullanıcı rolü değiştir.
        POST /api/v1/users/{id}/change_role/
        """
        user = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in dict(User.Role.choices):
            return Response(
                {'error': 'Geçersiz rol.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Super admin rolü sadece super admin verebilir
        if new_role == User.Role.SUPER_ADMIN:
            if request.user.role != User.Role.SUPER_ADMIN:
                return Response(
                    {'error': 'Bu rolü atama yetkiniz yok.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        
        user.role = new_role
        user.save()
        
        return Response(UserSerializer(user).data)

