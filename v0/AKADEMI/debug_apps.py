import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'akademi.settings_test')
django.setup()

print("INSTALLED_APPS:")
for app in settings.INSTALLED_APPS:
    print(f" - {app}")

print("\nLOADED MODELS:")
from django.apps import apps
for model in apps.get_models():
    print(f" - {model._meta.label}")

print("\nTenants Config:")
try:
    print(apps.get_app_config('tenants'))
except Exception as e:
    print(f"Error getting tenants config: {e}")
