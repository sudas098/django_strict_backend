import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class DocumentRole(models.TextChoices):
    VIEWER = "viewer", "Viewer"
    EDITOR = "editor", "Editor"

class Document(models.Model):
    """Represents a collaborative document."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    title = models.CharField(max_length=255, db_index=True)
    content = models.TextField(blank=True, default="")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_documents",
        db_index=True
    )
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "documents"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

class DocumentMember(models.Model):
    """Represents a access permossion granted to a user for a specific document."""
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_memberships"
    )
    role = models.CharField(
        max_length=20,
        choices=DocumentRole.choices,
        default=DocumentRole.VIEWER,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "document_members"
        constraints = [
            models.UniqueConstraint(
                fields=["document", "user"],
                name="unique_document_member",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user.email} - {self.document.title} ({self.role})"
