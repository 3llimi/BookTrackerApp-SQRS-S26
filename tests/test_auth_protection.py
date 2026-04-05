from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


# helpers


def register_and_login(email="test@test.com", password="password123"):
    """Register a user and return their auth token"""
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Returns the Authorization header dict"""
    return {"Authorization": f"Bearer {token}"}


# auth protection tests
def test_books_requires_auth():
    # no token return 401
    response = client.get("/api/v1/books/")
    assert response.status_code == 401


def test_books_with_valid_token():
    token = register_and_login("user1@test.com")
    response = client.get("/api/v1/books/", headers=auth_headers(token))
    assert response.status_code == 200


def test_invalid_token_returns_401():
    response = client.get(
        "/api/v1/books/", headers={"Authorization": "Bearer totally.fake.token"}
    )
    assert response.status_code == 401


# per-user isolation tests
def test_user_cannot_see_other_users_books():
    # User A creates a book
    token_a = register_and_login("usera@test.com")
    create_res = client.post(
        "/api/v1/books/",
        json={"title": "User A Book", "author": "Author A"},
        headers=auth_headers(token_a),
    )
    book_id = create_res.json()["id"]

    # User B tries to access it → 404 (not 403, don't leak existence)
    token_b = register_and_login("userb@test.com")
    response = client.get(f"/api/v1/books/{book_id}", headers=auth_headers(token_b))
    assert response.status_code == 404


def test_user_only_sees_their_own_books():
    token_a = register_and_login("alpha@test.com")
    token_b = register_and_login("beta@test.com")

    # User A creates a book
    client.post(
        "/api/v1/books/",
        json={"title": "Alpha Book", "author": "Author"},
        headers=auth_headers(token_a),
    )

    # User B lists books — should NOT see User A's book
    response = client.get("/api/v1/books/", headers=auth_headers(token_b))
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "Alpha Book" not in titles


def test_user_can_delete_own_book():
    token = register_and_login("owner@test.com")
    create_res = client.post(
        "/api/v1/books/",
        json={"title": "My Book", "author": "Me"},
        headers=auth_headers(token),
    )
    book_id = create_res.json()["id"]

    response = client.delete(f"/api/v1/books/{book_id}", headers=auth_headers(token))
    assert response.status_code == 204


def test_user_cannot_delete_other_users_book():
    token_a = register_and_login("owner2@test.com")
    create_res = client.post(
        "/api/v1/books/",
        json={"title": "Protected Book", "author": "Owner"},
        headers=auth_headers(token_a),
    )
    book_id = create_res.json()["id"]

    token_b = register_and_login("thief@test.com")
    response = client.delete(f"/api/v1/books/{book_id}", headers=auth_headers(token_b))
    assert response.status_code == 404  # 404 not 403 — don't leak existence
