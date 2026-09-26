from django.db import transaction
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers import UserRegistrationSerializer, UserSerializer


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
