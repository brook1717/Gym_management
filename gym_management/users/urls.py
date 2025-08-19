from django.urls import path
from .views import Registeration_view, Login_view, Logout_view
from .session_authentication import SessionLoginView, SessionLogoutView, get_csrf_token
urlpatterns = [
    path('register/', Registeration_view.as_view()),
    path('login/', Login_view.as_view()),
    path('logout/', Logout_view.as_view()),


     # Session Authentication Endpoints (for demo/testing only)
    path('session/login/', SessionLoginView.as_view(), name='session-login'),
    path('session/logout/', SessionLogoutView.as_view(), name='session-logout'),
    path('session/csrf/', get_csrf_token, name='session-csrf'),
]