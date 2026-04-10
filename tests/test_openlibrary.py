from unittest.mock import patch, MagicMock
from uuid import uuid4
import httpx


def get_auth_headers(client, email=None, password="password123"):
    if email is None:
        email = f"openlibrary-{uuid4().hex[:8]}@test.com"

    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# mock response helper
def mock_response(json_data: dict, status_code: int = 200):
    """Creates a fake httpx response object"""
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()  # does nothing by default
    return mock


# search tests
def test_search_returns_simplified_list(client):
    headers = get_auth_headers(client)
    fake_response = {
        "docs": [
            {
                "title": "Dune",
                "author_name": ["Frank Herbert"],
                "isbn": ["9780441013593"],
                "cover_i": 12345,
                "first_publish_year": 1965,
                "subject": ["Science Fiction", "Space opera"],
                "number_of_pages_median": 412,
            }
        ]
    }

    with patch("httpx.get", return_value=mock_response(fake_response)):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Dune"
    assert data[0]["author"] == "Frank Herbert"
    assert data[0]["isbn"] == "9780441013593"
    assert "covers.openlibrary.org" in data[0]["cover_url"]
    assert data[0]["genre"] == "Science Fiction"
    assert data[0]["total_pages"] == 412


def test_search_handles_missing_fields(client):
    headers = get_auth_headers(client)
    # some Open Library docs have missing fields — should not crash
    fake_response = {"docs": [{"title": "Some Book"}]}  # no author, isbn, cover_i

    with patch("httpx.get", return_value=mock_response(fake_response)):
        response = client.get("/api/v1/openlibrary/search?q=something", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data[0]["author"] is None
    assert data[0]["isbn"] is None
    assert data[0]["cover_url"] is None
    assert data[0]["genre"] is None
    assert data[0]["total_pages"] is None


# ISBN lookup tests
def test_get_book_by_isbn(client):
    headers = get_auth_headers(client)
    fake_response = {
        "title": "Dune",
        "number_of_pages": 412,
        "covers": [12345],
        "authors": [{"key": "/authors/OL123A"}],
        "subjects": [{"name": "Science Fiction"}, {"name": "Adventure"}],
    }

    with patch("httpx.get", return_value=mock_response(fake_response)):
        response = client.get("/api/v1/openlibrary/book/9780441013593", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Dune"
    assert data["total_pages"] == 412
    assert data["isbn"] == "9780441013593"
    assert "covers.openlibrary.org" in data["cover_url"]
    assert data["genre"] == "Science Fiction"


# error handling tests
def test_timeout_returns_503(client):
    headers = get_auth_headers(client)
    with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)
    assert response.status_code == 503


def test_connection_error_returns_503(client):
    headers = get_auth_headers(client)
    with patch("httpx.get", side_effect=httpx.ConnectError("connection failed")):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)
    assert response.status_code == 503


def test_malformed_json_returns_502(client):
    headers = get_auth_headers(client)
    mock = MagicMock()
    mock.raise_for_status = MagicMock()
    mock.json.side_effect = ValueError("malformed json")

    with patch("httpx.get", return_value=mock):
        response = client.get("/api/v1/openlibrary/search?q=dune", headers=headers)
    assert response.status_code == 502
