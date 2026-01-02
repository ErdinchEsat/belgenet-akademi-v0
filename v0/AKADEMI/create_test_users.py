from django.contrib.auth import get_user_model
from core.models import UserRole
import os

User = get_user_model()

users = [
    {
        'email': 'student@test.com',
        'password': 'Test123!',
        'first_name': 'Test',
        'last_name': 'Öğrenci',
        'role': UserRole.STUDENT
    },
    {
        'email': 'instructor@test.com',
        'password': 'Test123!',
        'first_name': 'Test',
        'last_name': 'Eğitmen',
        'role': UserRole.INSTRUCTOR
    },
    {
        'email': 'admin@test.com',
        'password': 'Test123!',
        'first_name': 'Test',
        'last_name': 'Admin',
        'role': UserRole.TENANT_ADMIN
    },
    {
        'email': 'super@test.com',
        'password': 'Test123!',
        'first_name': 'Super',
        'last_name': 'Admin',
        'role': UserRole.SUPER_ADMIN,
        'is_superuser': True,
        'is_staff': True
    }
]

for user_data in users:
    email = user_data['email']
    if not User.objects.filter(email=email).exists():
        print(f"Creating user {email}...")
        is_superuser = user_data.pop('is_superuser', False)
        is_staff = user_data.pop('is_staff', False)
        
        user = User.objects.create_user(**user_data)
        if is_superuser:
            user.is_superuser = True
        if is_staff:
            user.is_staff = True
        user.save()
        print(f"User {email} created.")
    else:
        print(f"User {email} already exists.")
