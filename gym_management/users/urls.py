from django.urls import path
from .views import (
    Registeration_view, Login_view, Logout_view, TokenRefreshView,
    UserListView, UserDetailView, UserProfileView,
)
from .session_authentication import SessionLoginView, SessionLogoutView, get_csrf_token

urlpatterns = [
    #JWT Authentication (tokens stored in HttpOnly cookies)
    path('register/', Registeration_view.as_view(), name='register'),
    path('login/', Login_view.as_view(), name='login'),
    path('logout/', Logout_view.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Session Authentication Endpoints (for demo/testing only)
    path('session/login/', SessionLoginView.as_view(), name='session-login'),
    path('session/logout/', SessionLogoutView.as_view(), name='session-logout'),
    path('session/csrf/', get_csrf_token, name='session-csrf'),

    #User Management based on permissions
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
]