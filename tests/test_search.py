# tests/test_search.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

# Helper functions
def create_book(title, author, genre=None, total_pages=300):
    res = client.post("/api/v1/books/", json={
        "title": title,
        "author": author,
        "genre": genre,
        "total_pages": total_pages
    })
    return res.json()["id"]

def add_progress(book_id, status, rating=5):
    client.post(f"/api/v1/books/{book_id}/progress", json={
        "status": status,
        "rating": rating
    })

def setup_books():
    id1 = create_book("Dune", "Frank Herbert", genre="Sci-Fi")
    id2 = create_book("Dune Messiah", "Frank Herbert", genre="Sci-Fi")
    id3 = create_book("The Hobbit", "J.R.R. Tolkien", genre="Fantasy")
    
    # use valid statuses
    add_progress(id1, "finished")
    add_progress(id2, "reading")
    add_progress(id3, "not_started")
    
    return id1, id2, id3

# Tests
def test_search_by_q_title():
    setup_books()
    response = client.get("/api/v1/books/search?q=dune")
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "Dune" in titles
    assert "Dune Messiah" in titles
    assert "The Hobbit" not in titles

def test_search_by_q_author():
    setup_books()
    response = client.get("/api/v1/books/search?q=tolkien")
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert "The Hobbit" in titles

def test_filter_by_genre():
    setup_books()
    response = client.get("/api/v1/books/search?genre=Fantasy")
    assert response.status_code == 200
    for book in response.json():
        assert book["genre"] == "Fantasy"

def test_filter_by_status():
    setup_books()
    response = client.get("/api/v1/books/search?status=finished")
    assert response.status_code == 200
    for book in response.json():
        assert book["progress"]["status"] == "finished"

def test_sort_by_title_asc():
    setup_books()
    response = client.get("/api/v1/books/search?sort=title&order=asc")
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()]
    assert titles == sorted(titles)

def test_composable_filters():
    setup_books()
    response = client.get("/api/v1/books/search?q=dune&genre=Sci-Fi&sort=title&order=asc")
    assert response.status_code == 200
    for book in response.json():
        assert "dune" in book["title"].lower()
        assert book["genre"] == "Sci-Fi"

def test_invalid_sort_field():
    response = client.get("/api/v1/books/search?sort=invalid_field")
    assert response.status_code == 422

def test_no_filters_returns_all():
    setup_books()
    response = client.get("/api/v1/books/search")
    assert response.status_code == 200
    assert isinstance(response.json(), list)