from django.urls import path
from .views import (
    Registeration_view, Login_view, Logout_view, TokenRefreshView,
    SendVerificationEmailView, VerifyEmailView,
    PasswordResetView, PasswordResetConfirmView,
    UserListView, UserDetailView, UserProfileView,
    MemberProfileView, TrainerMemberListView, SystemSettingsView,
)
from .session_authentication import SessionLoginView, SessionLogoutView, get_csrf_token

urlpatterns = [
    #JWT Authentication (tokens stored in HttpOnly cookies)
    path('register/', Registeration_view.as_view(), name='register'),
    path('login/', Login_view.as_view(), name='login'),
    path('logout/', Logout_view.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Email Verification
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-email/resend/', SendVerificationEmailView.as_view(), name='verify-email-resend'),

    # Password Reset
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # Session Authentication Endpoints (for demo/testing only)
    path('session/login/', SessionLoginView.as_view(), name='session-login'),
    path('session/logout/', SessionLogoutView.as_view(), name='session-logout'),
    path('session/csrf/', get_csrf_token, name='session-csrf'),

    #User Management based on permissions
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    # Authorization demos
    path('me/member-profile/', MemberProfileView.as_view(), name='member-profile'),
    path('trainer/members/', TrainerMemberListView.as_view(), name='trainer-member-list'),
    path('system/settings/', SystemSettingsView.as_view(), name='system-settings'),
]