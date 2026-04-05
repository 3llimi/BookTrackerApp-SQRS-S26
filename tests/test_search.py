# tests/test_search.py
from fastapi.testclient import TestClient
from uuid import uuid4
from src.main import app

client = TestClient(app)


# Helper functions
def get_auth_headers(email=None, password="password123"):
    if email is None:
        email = f"search-{uuid4().hex[:8]}@test.com"

    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_book(title, author, headers, genre=None, total_pages=300):
    res = client.post(
        "/api/v1/books/",
        json={
            "title": title,
            "author": author,
            "genre": genre,
            "total_pages": total_pages,
        },
        headers=headers,
    )
    return res.json()["id"]


def add_progress(book_id, headers, status, rating=5):
    client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": status, "rating": rating},
        headers=headers,
    )


def setup_books(headers):
    id1 = create_book("Dune", "Frank Herbert", headers=headers, genre="Sci-Fi")
    id2 = create_book("Dune Messiah", "Frank Herbert", headers=headers, genre="Sci-Fi")
    id3 = create_book("The Hobbit", "J.R.R. Tolkien", headers=headers, genre="Fantasy")

    # use valid statuses
    add_progress(id1, headers, "finished")
    add_progress(id2, headers, "reading")
    add_progress(id3, headers, "not_started")

    return id1, id2, id3


# Tests
def test_search_by_q_title():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search?q=dune", headers=headers)
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "Dune" in titles
    assert "Dune Messiah" in titles
    assert "The Hobbit" not in titles


def test_search_by_q_author():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search?q=tolkien", headers=headers)
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "The Hobbit" in titles


def test_filter_by_genre():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search?genre=Fantasy", headers=headers)
    assert response.status_code == 200
    for book in response.json():
        assert book["genre"] == "Fantasy"


def test_filter_by_status():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search?status=finished", headers=headers)
    assert response.status_code == 200
    for book in response.json():
        assert book["progress"]["status"] == "finished"


def test_sort_by_title_asc():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search?sort=title&order=asc", headers=headers)
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert titles == sorted(titles)


def test_composable_filters():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get(
        "/api/v1/books/search?q=dune&genre=Sci-Fi&sort=title&order=asc", headers=headers
    )
    assert response.status_code == 200
    for book in response.json():
        assert "dune" in book["title"].lower()
        assert book["genre"] == "Sci-Fi"


def test_invalid_sort_field():
    headers = get_auth_headers()
    response = client.get("/api/v1/books/search?sort=invalid_field", headers=headers)
    assert response.status_code == 422


def test_no_filters_returns_all():
    headers = get_auth_headers()
    setup_books(headers)
    response = client.get("/api/v1/books/search", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
