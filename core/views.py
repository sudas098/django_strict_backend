from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Unauthenticated system liveness probs for monitoring system"""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        return Response({'status': 'ok'}, status=status.HTTP_200_OK)
