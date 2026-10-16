import pytest
from rest_framework import status
from rest_framework.test import APIClient

from core.factories import UserFactory
from documents.factories import DocumentFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestDocumentAsyncExport:
    def test_export_action_enqueues_task(self, api_client: APIClient) -> None:
        user = UserFactory.create()
        doc = DocumentFactory.create(owner=user)
        api_client.force_authenticate(user=user)

        response = api_client.post(f"/api/documents/{doc.id}/export/")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "task_id" in response.data
        assert response.data["status"] == "queued"
