from uuid import uuid4
import pytest

PROGRESS_RESPONSE_FIELDS = {
    "id",
    "status",
    "current_page",
    "rating",
    "notes",
    "updated_at",
    "progress_percentage",
}


def register_and_login(client, email=None, password="password123"):
    if email is None:
        email = f"progress-{uuid4().hex[:8]}@test.com"

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


def create_book(client, headers, total_pages=300):
    response = client.post(
        "/api/v1/books/",
        json={
            "title": "Test Book",
            "author": "Test Author",
            "total_pages": total_pages,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.mark.parametrize(
    "method,url,payload",
    [
        ("post", "/api/v1/books/1/progress", {"status": "reading", "current_page": 10}),
        ("get", "/api/v1/books/1/progress", None),
        ("patch", "/api/v1/books/1/progress", {"current_page": 20}),
    ],
)
def test_progress_endpoints_require_auth(client, method, url, payload):
    request = getattr(client, method)

    if payload is None:
        response = request(url)
    else:
        response = request(url, json=payload)

    assert response.status_code == 401


def test_create_progress_success(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50, "rating": 4},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()

    assert set(data.keys()) == PROGRESS_RESPONSE_FIELDS
    assert data["status"] == "reading"
    assert data["current_page"] == 50
    assert data["rating"] == 4


def test_create_progress_duplicate_returns_409(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    first = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 10},
        headers=headers,
    )
    second = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 20},
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Progress already exists for this book"


def test_create_progress_missing_book_returns_404(client):
    headers = register_and_login(client)

    response = client.post(
        "/api/v1/books/9999/progress",
        json={"status": "reading", "current_page": 10},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_create_progress_current_page_exceeds_total_pages_returns_422(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers, total_pages=200)

    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 999},
        headers=headers,
    )

    assert response.status_code == 422
    assert "cannot exceed" in response.json()["detail"]


def test_get_progress_success(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 30},
        headers=headers,
    )

    response = client.get(f"/api/v1/books/{book_id}/progress", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == PROGRESS_RESPONSE_FIELDS
    assert data["status"] == "reading"
    assert data["current_page"] == 30


def test_get_progress_without_record_returns_404(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    response = client.get(f"/api/v1/books/{book_id}/progress", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "No progress record found for this book"


def test_patch_progress_partial_success(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50, "rating": 3},
        headers=headers,
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": 100},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == PROGRESS_RESPONSE_FIELDS
    assert data["current_page"] == 100
    assert data["status"] == "reading"
    assert data["rating"] == 3


@pytest.mark.parametrize(
    "new_page,expected_status",
    [
        (0, "not_started"),
        (100, "reading"),
        (300, "completed"),
    ],
)
def test_patch_progress_status_transitions(client, new_page, expected_status):
    headers = register_and_login(client)
    book_id = create_book(client, headers, total_pages=300)

    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50},
        headers=headers,
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": new_page},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["current_page"] == new_page
    assert response.json()["status"] == expected_status


def test_patch_progress_invalid_rating_returns_422(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50},
        headers=headers,
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"rating": 6},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Rating must be between 1 and 5"


def test_patch_progress_current_page_exceeds_total_pages_returns_422(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers, total_pages=200)

    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50},
        headers=headers,
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": 999},
        headers=headers,
    )

    assert response.status_code == 422
    assert "cannot exceed" in response.json()["detail"]


def test_nested_progress_visible_in_get_book(client):
    headers = register_and_login(client)
    book_id = create_book(client, headers)

    create_response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 80, "rating": 5},
        headers=headers,
    )
    assert create_response.status_code == 201

    response = client.get(f"/api/v1/books/{book_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert data["progress"] is not None
    assert set(data["progress"].keys()) == PROGRESS_RESPONSE_FIELDS
    assert data["progress"]["status"] == "reading"
    assert data["progress"]["current_page"] == 80
    assert data["progress"]["rating"] == 5
