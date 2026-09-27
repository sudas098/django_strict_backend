from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from core.views import (
    CurrentUserView,
    CustomTokenObtainPairView,
    HealthCheckView,
    RegisterView,
)

urlpatterns = [
    path('health', HealthCheckView.as_view(), name='health'),
    path('auth/register', RegisterView.as_view(), name='auth_register'),
    path('auth/token', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/me', CurrentUserView.as_view(), name='current_user')
]
