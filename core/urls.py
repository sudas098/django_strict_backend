from django.urls import path

from core.views import HealthCheckView, RegisterView

urlpatterns = [
    path('health', HealthCheckView.as_view(), name='health'),
    path('auth/register', RegisterView.as_view(), name='auth/register')
]
