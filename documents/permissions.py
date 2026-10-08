from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from documents.models import Document, DocumentMember, DocumentRole


class IsDocumentCollaborator(permissions.BasePermission):
    """Granual object permissions for documents

    - Owners have full access (view, edit, delete) .
    - Editors can view and edit, but can not delete .
    - Viewer have read-only access .
    """

    def has_object_permission(
            self,
            request: Request,
            view: APIView,
            obj: Document
    ) -> bool:
        user = request.user

        if not user.is_authenticated:
            return False

        #1. Document owner has complete authorization
        if obj.owner_id == user.id:
            return True

        #2. Check collaborator membership
        membership = DocumentMember.objects.filter(
            document=obj,
            user=user,
        ).first()

        if not membership:
            return False

        #3. Read access for any active member
        if request.method in permissions.SAFE_METHODS:
            return True

        #4. Write access("PUT", "PATCH") for editors only
        if request.method in ("PUT", "PATCH"):
            return membership.role == DocumentRole.EDITOR

        #5. Delete restricted to owner only
        return False
