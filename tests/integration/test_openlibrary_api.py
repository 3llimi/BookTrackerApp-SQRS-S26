from uuid import uuid4
from unittest.mock import patch
import httpx


class MockResponse:
    def __init__(
        self,
        json_data=None,
        *,
        json_side_effect=None,
        raise_for_status_exc=None,
    ):
        self._json_data = json_data
        self._json_side_effect = json_side_effect
        self._raise_for_status_exc = raise_for_status_exc

    def raise_for_status(self):
        if self._raise_for_status_exc:
            raise self._raise_for_status_exc

    def json(self):
        if self._json_side_effect:
            raise self._json_side_effect
        return self._json_data


def register_and_login(client, email=None, password="password123"):
    if email is None:
        email = f"openlibrary-{uuid4().hex[:8]}@test.com"

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_openlibrary_search_requires_auth(client):
    response = client.get("/api/v1/openlibrary/search?q=dune")
    assert response.status_code == 401


def test_openlibrary_book_requires_auth(client):
    response = client.get("/api/v1/openlibrary/book/9780441013593")
    assert response.status_code == 401


def test_openlibrary_search_success(client):
    headers = register_and_login(client)
    fake_response = {
        "docs": [
            {
                "title": "Dune",
                "author_name": ["Frank Herbert"],
                "isbn": ["9780441013593"],
                "cover_i": 12345,
                "first_publish_year": 1965,
            }
        ]
    }

    with patch(
        "src.services.openlibrary_service.httpx.get",
        return_value=MockResponse(json_data=fake_response),
    ):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Dune"
    assert data[0]["author"] == "Frank Herbert"
    assert data[0]["isbn"] == "9780441013593"
    assert data[0]["first_publish_year"] == 1965
    assert "covers.openlibrary.org" in data[0]["cover_url"]


def test_openlibrary_search_empty_results(client):
    headers = register_and_login(client)

    with patch(
        "src.services.openlibrary_service.httpx.get",
        return_value=MockResponse(json_data={"docs": []}),
    ):
        response = client.get("/api/v1/openlibrary/search?q=unknown", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


def test_openlibrary_book_by_isbn_success(client):
    headers = register_and_login(client)
    fake_response = {
        "title": "Dune",
        "number_of_pages": 412,
        "covers": [12345],
    }

    with patch(
        "src.services.openlibrary_service.httpx.get",
        return_value=MockResponse(json_data=fake_response),
    ):
        response = client.get(
            "/api/v1/openlibrary/book/9780441013593",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()

    assert data["title"] == "Dune"
    assert data["isbn"] == "9780441013593"
    assert data["total_pages"] == 412
    assert data["author"] is None
    assert data["genre"] is None
    assert "covers.openlibrary.org" in data["cover_url"]


def test_openlibrary_timeout_returns_503(client):
    headers = register_and_login(client)

    with patch(
        "src.services.openlibrary_service.httpx.get",
        side_effect=httpx.TimeoutException("timeout"),
    ):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "Open Library request timed out"


def test_openlibrary_connection_error_returns_503(client):
    headers = register_and_login(client)

    with patch(
        "src.services.openlibrary_service.httpx.get",
        side_effect=httpx.ConnectError("connection failed"),
    ):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "Could not connect to Open Library"


def test_openlibrary_malformed_json_returns_502(client):
    headers = register_and_login(client)

    with patch(
        "src.services.openlibrary_service.httpx.get",
        return_value=MockResponse(json_side_effect=ValueError("bad json")),
    ):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert response.status_code == 502
    assert response.json()["detail"] == "Open Library returned malformed data"


def test_openlibrary_http_status_error_returns_503(client):
    headers = register_and_login(client)

    request = httpx.Request("GET", "https://openlibrary.org/search.json")
    response = httpx.Response(500, request=request)
    http_error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=response,
    )

    with patch(
        "src.services.openlibrary_service.httpx.get",
        return_value=MockResponse(raise_for_status_exc=http_error),
    ):
        api_response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert api_response.status_code == 503
    assert api_response.json()["detail"] == "Open Library returned an error"