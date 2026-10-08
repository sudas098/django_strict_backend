from typing import Any

from django.db.models import Q, QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from core.models import CustomUser
from documents.models import Document, DocumentMember, DocumentRole
from documents.permissions import IsDocumentCollaborator
from documents.serializers import (
    DocumentCreateUpdateSerializer,
    DocumentMemberAddSerializer,
    DocumentMemberSerializer,
    DocumentSerializer,
)


class DocumentViewSet(viewsets.ModelViewSet[Document]):
    """ViewSet for managing collaborative documents with scoped access."""

    permission_classes = [permissions.IsAuthenticated, IsDocumentCollaborator]

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

        if self.action == "add_member":
            return DocumentMemberAddSerializer
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

    @action(detail=True, methods=["POST"], url_path="members")
    def add_member(self, request: Request, pk: str | None = None) -> Response:
        """Invite a collaborater to the document (owner_only)."""
        document = self.get_object()

        if document.owner_id != request.user.id:
            return Response(
                {"error": "client_error",
                  "message": "Only document ower can manage members ."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_user = CustomUser.objects.get(email=serializer.validated_data["email"])
        role = serializer.validated_data.get("role", DocumentRole.VIEWER)

        if target_user.id == document.owner_id:
            return Response(
                {"error": "client_error",
                  "message": "Owner can't be added as a collaborater."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member, created = DocumentMember.objects.update_or_create(
            document=document,
            user=target_user,
            defaults={"role": role}
        )

        output = DocumentMemberSerializer(member)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
