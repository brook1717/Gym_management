# activity_logs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ActivityLogViewSet

router = DefaultRouter()
router.register(r'activity-logs', ActivityLogViewSet, basename='activity-log')

urlpatterns = router.urls
