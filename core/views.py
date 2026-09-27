from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from core.serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
)


class HealthCheckView(APIView):
    """Unauthenticated system liveness probs for monitoring system"""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)

class RegisterView(APIView):
    """User Registration endpoint protected by an explicit transaction boundary."""

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()

        output_serializer = UserSerializer(user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    """Issues access and refresh JWTs for valid credentials"""

    serializer_class = CustomTokenObtainPairSerializer

class CurrentUserView(APIView):
    """Return the authenticated user Profile"""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        assert request.user.is_authenticated
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
