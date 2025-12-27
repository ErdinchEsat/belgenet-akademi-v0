"""
User Serializers
================

Kullanıcı API serializer'ları.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Kullanıcı bilgileri serializer.
    Frontend User interface'i ile uyumlu.
    """
    
    name = serializers.CharField(source='full_name', read_only=True)
    tenantId = serializers.CharField(source='tenant_id', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'first_name',
            'last_name',
            'role',
            'avatar',
            'title',
            'tenantId',
            'points',
            'streak',
            'language',
            'notify_email',
            'notify_push',
            'date_joined',
            'last_login',
        ]
        read_only_fields = ['id', 'date_joined', 'last_login', 'points', 'streak']

    def get_avatar(self, obj) -> str:
        return obj.get_avatar_url()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Kullanıcı oluşturma serializer.
    Register endpoint için.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Şifreler eşleşmiyor.'
            })
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Kullanıcı güncelleme serializer.
    Profil düzenleme için.
    """

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'avatar',
            'title',
            'bio',
            'phone',
            'language',
            'timezone',
            'notify_email',
            'notify_push',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Şifre değiştirme serializer.
    """
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )
    new_password = serializers.CharField(
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'},
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
    )

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Şifreler eşleşmiyor.'
            })
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mevcut şifre yanlış.')
        return value


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Token serializer.
    Token'a ekstra kullanıcı bilgileri ekler.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Token'a ekstra claim'ler ekle
        token['email'] = user.email
        token['name'] = user.full_name
        token['role'] = user.role
        if user.tenant:
            token['tenant_id'] = str(user.tenant.id)
            token['tenant_slug'] = user.tenant.slug

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Response'a kullanıcı bilgilerini ekle
        data['user'] = UserSerializer(self.user).data

        return data


class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal kullanıcı bilgileri.
    Liste görünümleri ve ilişkili veriler için.
    """
    
    name = serializers.CharField(source='full_name', read_only=True)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'avatar', 'role']

    def get_avatar(self, obj) -> str:
        return obj.get_avatar_url()

