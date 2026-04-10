from uuid import uuid4

import pytest

from src.models import Progress

BOOK_RESPONSE_FIELDS = {
    "id",
    "title",
    "author",
    "isbn",
    "genre",
    "total_pages",
    "cover_url",
    "created_at",
    "progress",
    "progress_percentage",
}


def register_and_login(client, email=None, password="password123"):
    if email is None:
        email = f"user-{uuid4().hex[:8]}@test.com"

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


def create_book(client, headers, **overrides):
    payload = {
        "title": "Dune",
        "author": "Frank Herbert",
        "isbn": f"isbn-{uuid4().hex[:8]}",
        "genre": "Sci-Fi",
        "total_pages": 412,
    }
    payload.update(overrides)
    return client.post("/api/v1/books/", json=payload, headers=headers)


@pytest.mark.parametrize(
    "method,url,payload",
    [
        ("get", "/api/v1/books/", None),
        ("post", "/api/v1/books/", {"title": "Dune", "author": "Frank Herbert"}),
        ("get", "/api/v1/books/1", None),
        ("put", "/api/v1/books/1", {"title": "Updated"}),
        ("delete", "/api/v1/books/1", None),
    ],
)
def test_books_endpoints_require_auth(client, method, url, payload):
    request = getattr(client, method)

    if payload is None:
        response = request(url)
    else:
        response = request(url, json=payload)

    assert response.status_code == 401


def test_create_book_success(client):
    headers = register_and_login(client)

    response = create_book(client, headers)

    assert response.status_code == 201
    data = response.json()

    assert set(data.keys()) == BOOK_RESPONSE_FIELDS
    assert data["title"] == "Dune"
    assert data["author"] == "Frank Herbert"
    assert data["genre"] == "Sci-Fi"
    assert data["total_pages"] == 412
    assert data["progress"] is None


def test_create_book_missing_required_field_returns_422(client):
    headers = register_and_login(client)

    response = client.post(
        "/api/v1/books/",
        json={"title": "Dune"},
        headers=headers,
    )

    assert response.status_code == 422


def test_create_book_duplicate_isbn_returns_409(client):
    headers = register_and_login(client)

    first = create_book(client, headers, isbn="duplicate-123")
    second = create_book(client, headers, isbn="duplicate-123", title="Another Book")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Book with this ISBN already exists"


def test_list_books_returns_only_current_users_books(client):
    headers_a = register_and_login(client, email="alpha@test.com")
    headers_b = register_and_login(client, email="beta@test.com")

    create_book(client, headers_a, title="Alpha Book")
    create_book(client, headers_b, title="Beta Book")

    response = client.get("/api/v1/books/", headers=headers_a)

    assert response.status_code == 200
    data = response.json()
    titles = [book["title"] for book in data]

    assert "Alpha Book" in titles
    assert "Beta Book" not in titles


def test_get_book_success(client):
    headers = register_and_login(client)
    created = create_book(client, headers, title="Get Me")

    book_id = created.json()["id"]
    response = client.get(f"/api/v1/books/{book_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert set(data.keys()) == BOOK_RESPONSE_FIELDS
    assert data["id"] == book_id
    assert data["title"] == "Get Me"


def test_get_book_not_found_returns_404(client):
    headers = register_and_login(client)

    response = client.get("/api/v1/books/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_get_other_users_book_returns_404(client):
    headers_a = register_and_login(client, email="owner@test.com")
    headers_b = register_and_login(client, email="other@test.com")

    created = create_book(client, headers_a, title="Private Book")
    book_id = created.json()["id"]

    response = client.get(f"/api/v1/books/{book_id}", headers=headers_b)

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_update_book_partial_success(client):
    headers = register_and_login(client)
    created = create_book(client, headers, title="Old Title", author="Original Author")
    book_id = created.json()["id"]

    response = client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "New Title"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == book_id
    assert data["title"] == "New Title"
    assert data["author"] == "Original Author"


def test_update_book_not_found_returns_404(client):
    headers = register_and_login(client)

    response = client.put(
        "/api/v1/books/9999",
        json={"title": "No book here"},
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_delete_book_success(client):
    headers = register_and_login(client)
    created = create_book(client, headers, title="Delete Me")
    book_id = created.json()["id"]

    delete_response = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    get_response = client.get(f"/api/v1/books/{book_id}", headers=headers)

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_delete_book_not_found_returns_404(client):
    headers = register_and_login(client)

    response = client.delete("/api/v1/books/9999", headers=headers)

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_delete_book_cascades_progress(client, db_session):
    headers = register_and_login(client)
    created = create_book(client, headers, title="Tracked Book", total_pages=300)
    book_id = created.json()["id"]

    progress_response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 100},
        headers=headers,
    )
    assert progress_response.status_code == 201

    progress_in_db = (
        db_session.query(Progress).filter(Progress.book_id == book_id).first()
    )
    assert progress_in_db is not None

    delete_response = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert delete_response.status_code == 204

    progress_after_delete = (
        db_session.query(Progress).filter(Progress.book_id == book_id).first()
    )
    assert progress_after_delete is None

def test_books_with_invalid_token_return_401(client):
    response = client.get(
        "/api/v1/books/",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert response.status_code == 401


def test_update_other_users_book_returns_404(client):
    headers_a = register_and_login(client, email="owner-update@test.com")
    headers_b = register_and_login(client, email="intruder-update@test.com")

    created = create_book(client, headers_a, title="Owner Book")
    book_id = created.json()["id"]

    response = client.put(
        f"/api/v1/books/{book_id}",
        json={"title": "Hacked Title"},
        headers=headers_b,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_delete_other_users_book_returns_404(client):
    headers_a = register_and_login(client, email="owner-delete@test.com")
    headers_b = register_and_login(client, email="intruder-delete@test.com")

    created = create_book(client, headers_a, title="Protected Book")
    book_id = created.json()["id"]

    response = client.delete(f"/api/v1/books/{book_id}", headers=headers_b)

    assert response.status_code == 404
    assert response.json()["detail"] == "Book not found"


def test_duplicate_isbn_is_allowed_for_different_users(client):
    headers_a = register_and_login(client, email="isbn-a@test.com")
    headers_b = register_and_login(client, email="isbn-b@test.com")

    first = create_book(client, headers_a, isbn="shared-isbn-123", title="Alpha Copy")
    second = create_book(client, headers_b, isbn="shared-isbn-123", title="Beta Copy")

    assert first.status_code == 201
    assert second.status_code == 201


def test_get_book_includes_progress_percentage(client):
    headers = register_and_login(client, email="percentage@test.com")
    created = create_book(client, headers, title="Measured Book", total_pages=300)
    book_id = created.json()["id"]

    progress_response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 150, "rating": 4},
        headers=headers,
    )
    assert progress_response.status_code == 201

    response = client.get(f"/api/v1/books/{book_id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["progress"] is not None
    assert data["progress"]["current_page"] == 150
    assert data["progress_percentage"] == 50.0
    
    
# negative total_pages on create
def test_create_book_negative_total_pages_returns_422(client):
    headers = register_and_login(client, email="negative-pages-create@test.com")

    response = client.post(
        "/api/v1/books/",
        json={
            "title": "Bad Book",
            "author": "Bad Author",
            "total_pages": -1,
        },
        headers=headers,
    )

    assert response.status_code == 422
    
    
# negative total_pages on update
def test_update_book_negative_total_pages_returns_422(client):
    headers = register_and_login(client, email="negative-pages-update@test.com")
    created = create_book(client, headers, title="Normal Book", total_pages=300)
    book_id = created.json()["id"]

    response = client.put(
        f"/api/v1/books/{book_id}",
        json={"total_pages": -5},
        headers=headers,
    )

    assert response.status_code == 422
    
    
# pagination behavior
def test_list_books_respects_limit_and_offset(client):
    headers = register_and_login(client, email="pagination@test.com")

    create_book(client, headers, title="Book A")
    create_book(client, headers, title="Book B")
    create_book(client, headers, title="Book C")

    response = client.get(
        "/api/v1/books/?sort=title&order=asc&limit=1&offset=1",
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Book B"