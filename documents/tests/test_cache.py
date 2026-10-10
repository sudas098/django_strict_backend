
import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient

from core.factories import UserFactory
from documents.factories import DocumentFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestDocumentCache:
    def test_retrieve_uses_cache_on_subsequent_reads(
        self, api_client: APIClient, django_assert_num_queries
    ) -> None:
        cache.clear()
        user = UserFactory.create()
        doc = DocumentFactory.create(owner=user)
        api_client.force_authenticate(user=user)

        # First read: Cache MISS -> executes DB query
        res1 = api_client.get(f"/api/documents/{doc.id}/")
        assert res1.status_code == status.HTTP_200_OK

        # Second read: Cache HIT -> exactly 0 database queries
        with django_assert_num_queries(0):
            res2 = api_client.get(f"/api/documents/{doc.id}/")

        assert res2.status_code == status.HTTP_200_OK
        assert res2.data["id"] == str(doc.id)

    def test_update_invalidates_cache(self, api_client: APIClient) -> None:
        cache.clear()
        user = UserFactory.create()
        doc = DocumentFactory.create(owner=user, title="Original Title")
        api_client.force_authenticate(user=user)

        # Warm the cache
        api_client.get(f"/api/documents/{doc.id}/")
        assert cache.get(f"doc:{doc.id}") is not None

        # Mutate document
        res = api_client.patch(
            f"/api/documents/{doc.id}/",
            {"title": "Updated Title"},
            format="json",
        )
        assert res.status_code == status.HTTP_200_OK

        # Ensure cache key is evicted
        assert cache.get(f"doc:{doc.id}") is None
