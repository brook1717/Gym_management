from django.urls import path
from .views import Registeration_view, Login_view
urlpatterns = [
    path('register/', Registeration_view.as_view()),
    path('login/', Login_view.as_view()),
]