# tests/test_books.py
from fastapi.testclient import TestClient
from uuid import uuid4
from src.main import app

client = TestClient(app)


def get_auth_headers(email=None, password="password123"):
    if email is None:
        email = f"books-{uuid4().hex[:8]}@test.com"

    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_book():
    headers = get_auth_headers()
    response = client.post(
        "/api/v1/books/",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": "9780441013593"},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Dune"


def test_create_book_missing_author():
    headers = get_auth_headers()
    response = client.post("/api/v1/books/", json={"title": "Dune"}, headers=headers)
    assert response.status_code == 422  # FastAPI auto-validates required fields


def test_list_books():
    headers = get_auth_headers()
    response = client.get("/api/v1/books/", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_book_not_found():
    headers = get_auth_headers()
    response = client.get("/api/v1/books/9999", headers=headers)
    assert response.status_code == 404


def test_duplicate_isbn():
    headers = get_auth_headers()
    client.post(
        "/api/v1/books/",
        json={"title": "Dune", "author": "Frank Herbert", "isbn": "DUPLICATE123"},
        headers=headers,
    )
    response = client.post(
        "/api/v1/books/",
        json={
            "title": "Dune Part 2",
            "author": "Frank Herbert",
            "isbn": "DUPLICATE123",  # same ISBN → should 409
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_update_book_partial():
    headers = get_auth_headers()
    # Create first
    create = client.post(
        "/api/v1/books/",
        json={"title": "Old Title", "author": "Some Author"},
        headers=headers,
    )
    book_id = create.json()["id"]

    # Update only title
    response = client.put(
        f"/api/v1/books/{book_id}", json={"title": "New Title"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Some Author"  # untouched


def test_delete_book():
    headers = get_auth_headers()
    create = client.post(
        "/api/v1/books/",
        json={"title": "To Delete", "author": "Some Author"},
        headers=headers,
    )
    book_id = create.json()["id"]

    response = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert response.status_code == 204

    # Confirm it's gone
    response = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert response.status_code == 404
