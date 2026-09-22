from django.urls import path

from core.views import ErrorTriggerView, HealthCheckView

urlpatterns = [
    path('health', HealthCheckView.as_view(), name='health'),
]
