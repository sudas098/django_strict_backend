from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.models import CustomUser
from core.serializers import UserSerializer
from documents.models import Document, DocumentMember, DocumentRole

UserModel = get_user_model()


class DocumentMemberSerializer(serializers.ModelSerializer[DocumentMember]):
    """Read-only view of collaboration."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = DocumentMember
        fields = ["id", "user", "role", "created_at"]
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

class DocumentMemberAddSerializer(serializers.Serializer[dict[str, str]]):
    """Input serializer for adding collaboraters to a document ."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=DocumentRole.choices,
        default=DocumentRole.VIEWER,
    )

    def validate_email(self, value: str) -> str:
        clean_email = value.lower().strip()
        if not CustomUser.objects.filter(email=clean_email).exists():
            raise serializers.ValidationError("User with this email doesn't exists.")
        return clean_email
