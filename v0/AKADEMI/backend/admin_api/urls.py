"""
Admin API URLs
==============

Endpoints:
- /api/v1/admin/dashboard/ - Tenant Manager Dashboard
- /api/v1/admin/users/ - Kullanıcı yönetimi (CRUD, stats, bulk-import)
- /api/v1/admin/courses/ - Kurs kataloğu yönetimi
- /api/v1/admin/class-groups/ - Sınıf/grup yönetimi
- /api/v1/admin/logs/tech/ - Teknik loglar
- /api/v1/admin/logs/activity/ - Aktivite logları
- /api/v1/admin/finance/academies/ - Akademi finansları
- /api/v1/admin/finance/categories/ - Kategori gelirleri
- /api/v1/admin/finance/instructors/ - Eğitmen kazançları
- /api/v1/admin/live-sessions/ - Global canlı yayınlar
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TenantDashboardView,
    AdminUserViewSet,
    AdminCourseViewSet,
    AdminClassGroupViewSet,
    AdminOpsInboxViewSet,
    AdminReportsViewSet,
    AdminRolesViewSet,
    AdminTenantsViewSet,
    SystemStatsView,
    TechLogsViewSet,
    ActivityLogsViewSet,
    FinanceAcademiesView,
    FinanceCategoriesView,
    FinanceInstructorsView,
    GlobalLiveSessionsViewSet,
)

app_name = 'admin_api'

router = DefaultRouter()
router.register('users', AdminUserViewSet, basename='admin-users')
router.register('courses', AdminCourseViewSet, basename='admin-courses')
router.register('class-groups', AdminClassGroupViewSet, basename='admin-class-groups')
router.register('ops-inbox', AdminOpsInboxViewSet, basename='admin-ops-inbox')
router.register('reports', AdminReportsViewSet, basename='admin-reports')
router.register('roles', AdminRolesViewSet, basename='admin-roles')
router.register('tenants', AdminTenantsViewSet, basename='admin-tenants')
router.register('logs/tech', TechLogsViewSet, basename='tech-logs')
router.register('logs/activity', ActivityLogsViewSet, basename='activity-logs')
router.register('live-sessions', GlobalLiveSessionsViewSet, basename='live-sessions')

urlpatterns = [
    # Tenant Manager Dashboard
    path('dashboard/', TenantDashboardView.as_view(), name='tenant-dashboard'),
    
    # Router URLs
    path('', include(router.urls)),
    
    # Admin Courses - Custom Actions
    path('courses/stats/', AdminCourseViewSet.as_view({'get': 'stats'}), name='admin-courses-stats'),
    path('courses/categories/', AdminCourseViewSet.as_view({'get': 'categories'}), name='admin-courses-categories'),
    path('courses/bulk-action/', AdminCourseViewSet.as_view({'post': 'bulk_action'}), name='admin-courses-bulk-action'),
    path('courses/<int:pk>/approve/', AdminCourseViewSet.as_view({'post': 'approve'}), name='admin-courses-approve'),
    path('courses/<int:pk>/reject/', AdminCourseViewSet.as_view({'post': 'reject'}), name='admin-courses-reject'),
    path('courses/<int:pk>/unpublish/', AdminCourseViewSet.as_view({'post': 'unpublish'}), name='admin-courses-unpublish'),
    path('courses/<int:pk>/archive/', AdminCourseViewSet.as_view({'post': 'archive'}), name='admin-courses-archive'),
    path('courses/<int:pk>/restore/', AdminCourseViewSet.as_view({'post': 'restore'}), name='admin-courses-restore'),
    path('courses/<int:pk>/update-pricing/', AdminCourseViewSet.as_view({'post': 'update_pricing'}), name='admin-courses-pricing'),
    
    # Admin Class Groups - Custom Actions
    path('class-groups/stats/', AdminClassGroupViewSet.as_view({'get': 'stats'}), name='admin-class-groups-stats'),
    path('class-groups/<int:pk>/assign-students/', AdminClassGroupViewSet.as_view({'post': 'assign_students'}), name='admin-class-groups-assign-students'),
    path('class-groups/<int:pk>/assign-instructors/', AdminClassGroupViewSet.as_view({'post': 'assign_instructors'}), name='admin-class-groups-assign-instructors'),
    path('class-groups/<int:pk>/archive/', AdminClassGroupViewSet.as_view({'post': 'archive'}), name='admin-class-groups-archive'),
    path('class-groups/<int:pk>/activate/', AdminClassGroupViewSet.as_view({'post': 'activate'}), name='admin-class-groups-activate'),
    path('class-groups/<int:pk>/students/', AdminClassGroupViewSet.as_view({'get': 'students'}), name='admin-class-groups-students'),
    path('class-groups/<int:pk>/schedule/', AdminClassGroupViewSet.as_view({'get': 'schedule'}), name='admin-class-groups-schedule'),
    
    # Finance
    path('finance/academies/', FinanceAcademiesView.as_view(), name='finance-academies'),
    path('finance/categories/', FinanceCategoriesView.as_view(), name='finance-categories'),
    path('finance/instructors/', FinanceInstructorsView.as_view(), name='finance-instructors'),
    
    # System Stats (Super Admin Dashboard)
    path('system/stats/', SystemStatsView.as_view(), name='system-stats'),
    
    # Tenant Admin Search
    path('tenants/search-admins/', AdminTenantsViewSet.as_view({'get': 'search_admins'}), name='tenants-search-admins'),
]

