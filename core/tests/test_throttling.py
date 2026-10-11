import pytest
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()

@pytest.mark.django_db
class TestAuthThrottling:
    def test_registration_end_point_limited(
            self,
            api_client: APIClient
    ) -> None:
        cache.clear()

        #send 5 requests (allowed)
        for i in range(5):
            res = api_client.post(
                "/api/auth/register/",
                {"email": f"test{i}@example.com", "password": "StrongPassword123!"},
                format="json",
            )
            assert res.status_code == status.HTTP_201_CREATED

        #6th request must trigger HTTP 429
        blocked_res = api_client.post(
            "/api/auth/register/",
            {"email": "blocked@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        assert blocked_res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert blocked_res.data["error"] == "client_error"
