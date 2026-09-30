from typing import Any

from django.db.models import Q, QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.request import Request
from rest_framework.response import Response

from documents.models import Document
from documents.serializers import DocumentCreateUpdateSerializer, DocumentSerializer


class DocumentViewSet(viewsets.ModelViewSet[Document]):
    """ViewSet for managing collaborative documents with scoped access."""

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self) -> QuerySet[Document]:
        """Scope query to documents owned by user OR where user is a member.

        Uses select_related and prefetch_related to eliminate N+1 queries.
        """

        user = self.request.user
        return (
            Document.objects.filter(
                Q(owner=user) | Q(memberships__user=user)
            )
            .distinct()
            .select_related("owner")
            .prefetch_related("memberships__user")
        )

    def get_serializer_class(self) -> type[Any]:
        """Decouple input and output serialization schemas."""
        if self.action in ["create", "update", "partial_update"]:
            return DocumentCreateUpdateSerializer
        return DocumentSerializer

    def perform_create(self, serializer: Any) -> None:
        """Inject authenticated user as owner."""
        serializer.save(owner=self.request.user)

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """Create Document and Return complete DTO."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        output_serializer = DocumentSerializer(serializer.instance)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
