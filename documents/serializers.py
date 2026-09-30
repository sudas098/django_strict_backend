from rest_framework import serializers

from core.serializers import UserSerializer
from documents.models import Document, DocumentMember


class DocumentMemberSerializer(serializers.ModelSerializer[DocumentMember]):
    """Read-only view of collaboration."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = DocumentMember
        fields = ["id", "user", "role", "create_at"]
        read_only_fields = fields

class DocumentSerializer(serializers.ModelSerializer[Document]):
    """Detail Read representation of a document with owner and collaborations ."""

    owner = UserSerializer(read_only=True)
    memberships = DocumentMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "owner",
            "memberships",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "owner", "created_at", "updated_at"]

class DocumentCreateUpdateSerializer(serializers.ModelSerializer[Document]):
    """Write-only serializer for creating and updating only"""

    title = serializers.CharField(max_length=255, trim_whitespace=True)

    class Meta:
        model = Document
        fields = ["title", "content"]
