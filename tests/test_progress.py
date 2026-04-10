from fastapi.testclient import TestClient
from uuid import uuid4
from src.main import app

client = TestClient(app)


def get_auth_headers(email=None, password="password123"):
    if email is None:
        email = f"progress-{uuid4().hex[:8]}@test.com"

    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# helper to create a book to use in tests
def create_test_book(headers, total_pages=300):
    response = client.post(
        "/api/v1/books/",
        json={
            "title": "Test Book",
            "author": "Test Author",
            "total_pages": total_pages,
        },
        headers=headers,
    )
    return response.json()["id"]


def test_create_progress():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "reading"
    assert response.json()["current_page"] == 50


def test_create_progress_auto_reading_when_pages_above_zero():
    headers = get_auth_headers()
    book_id = create_test_book(headers, total_pages=300)

    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "not_started", "current_page": 1},
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "reading"
    assert response.json()["current_page"] == 1


def test_create_progress_409_if_already_exists():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )

    # second time → 409
    response = client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )
    assert response.status_code == 409


def test_create_progress_book_not_found():
    headers = get_auth_headers()
    response = client.post(
        "/api/v1/books/9999/progress", json={"status": "reading"}, headers=headers
    )
    assert response.status_code == 404


def test_get_progress():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )

    response = client.get(f"/api/v1/books/{book_id}/progress", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "reading"


def test_get_progress_404_if_none():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    response = client.get(f"/api/v1/books/{book_id}/progress", headers=headers)
    assert response.status_code == 404


def test_patch_progress_partial():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 50},
        headers=headers,
    )

    # only update current_page
    response = client.patch(
        f"/api/v1/books/{book_id}/progress", json={"current_page": 100}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["current_page"] == 100
    assert response.json()["status"] == "reading"  # untouched


def test_patch_progress_pages_exceed_total():
    headers = get_auth_headers()
    book_id = create_test_book(headers, total_pages=200)
    client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": 999},  # exceeds total_pages=200
        headers=headers,
    )
    assert response.status_code == 422


def test_patch_progress_invalid_rating():
    headers = get_auth_headers()
    book_id = create_test_book(headers)
    client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )

    response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"rating": 6},  # must be 1-5
        headers=headers,
    )
    assert response.status_code == 422


def test_auto_finish_when_pages_complete():
    headers = get_auth_headers()
    book_id = create_test_book(headers, total_pages=300)
    client.post(
        f"/api/v1/books/{book_id}/progress", json={"status": "reading"}, headers=headers
    )

    # set current_page == total_pages -> should auto-set status to completed
    response = client.patch(
        f"/api/v1/books/{book_id}/progress", json={"current_page": 300}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"  # auto-set
