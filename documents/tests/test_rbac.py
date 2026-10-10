import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.factories import UserFactory
from documents.factories import DocumentFactory, DocumentMemberFactory
from documents.models import DocumentRole


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestDocumentRBAC:
    def test_owner_can_delete_document(self, api_client: APIClient) -> None:
        owner = UserFactory.create()
        document = DocumentFactory.create(owner=owner)

        api_client.force_authenticate(user=owner)
        response = api_client.delete(f"/api/documents/{document.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_viewer_cannot_update_document(self, api_client: APIClient) -> None:
        owner = UserFactory.create()
        viewer = UserFactory.create()
        document = DocumentFactory.create(owner=owner)
        DocumentMemberFactory.create(
            document=document, user=viewer, role=DocumentRole.VIEWER
        )

        api_client.force_authenticate(user=viewer)
        response = api_client.patch(
            f"/api/documents/{document.id}/",
            {"title": "Unauthorized Title"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_viewer_cannot_delete_document(self, api_client: APIClient) -> None:
        owner = UserFactory.create()
        viewer = UserFactory.create()
        document = DocumentFactory.create(owner=owner)
        DocumentMemberFactory.create(
            document=document, user=viewer, role=DocumentRole.VIEWER
        )

        api_client.force_authenticate(user=viewer)
        response = api_client.delete(f"/api/documents/{document.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_editor_can_update_document(self, api_client: APIClient) -> None:
        owner = UserFactory.create()
        editor = UserFactory.create()
        document = DocumentFactory.create(owner=owner)
        DocumentMemberFactory.create(
            document=document, user=editor, role=DocumentRole.EDITOR
        )

        api_client.force_authenticate(user=editor)
        response = api_client.patch(
            f"/api/documents/{document.id}/",
            {"title": "Authorized Update"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        document.refresh_from_db()
        assert document.title == "Authorized Update"

    def test_list_documents_avoids_n_plus_one(
                self,
                api_client: APIClient,
                django_assert_num_queries
        ) -> None:
            user = UserFactory.create()
            api_client.force_authenticate(user=user)

            documents = DocumentFactory.create_batch(10, owner=user)
            for doc in documents:
                collab1 = UserFactory.create()
                collab2 = UserFactory.create()
                DocumentMemberFactory.create(document=doc, user=collab1)
                DocumentMemberFactory.create(document=doc, user=collab2)

            with django_assert_num_queries(3):
                response = api_client.get("/api/documents/")
                assert response.status_code == status.HTTP_200_OK
