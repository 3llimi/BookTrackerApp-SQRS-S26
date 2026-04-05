# tests/test_books.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_create_book():
    response = client.post("/api/v1/books/", json={
        "title": "Dune",
        "author": "Frank Herbert",
        "isbn": "9780441013593"
    })
    assert response.status_code == 201
    assert response.json()["title"] == "Dune"

def test_create_book_missing_author():
    response = client.post("/api/v1/books/", json={"title": "Dune"})
    assert response.status_code == 422   # FastAPI auto-validates required fields

def test_list_books():
    response = client.get("/api/v1/books/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_book_not_found():
    response = client.get("/api/v1/books/9999")
    assert response.status_code == 404

def test_duplicate_isbn():
    client.post("/api/v1/books/", json={
        "title": "Dune",
        "author": "Frank Herbert",
        "isbn": "DUPLICATE123"
    })
    response = client.post("/api/v1/books/", json={
        "title": "Dune Part 2",
        "author": "Frank Herbert",
        "isbn": "DUPLICATE123"    # same ISBN → should 409
    })
    assert response.status_code == 409

def test_update_book_partial():
    # Create first
    create = client.post("/api/v1/books/", json={
        "title": "Old Title",
        "author": "Some Author"
    })
    book_id = create.json()["id"]

    # Update only title
    response = client.put(f"/api/v1/books/{book_id}", json={"title": "New Title"})
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"
    assert response.json()["author"] == "Some Author"  # untouched

def test_delete_book():
    create = client.post("/api/v1/books/", json={
        "title": "To Delete",
        "author": "Some Author"
    })
    book_id = create.json()["id"]

    response = client.delete(f"/api/v1/books/{book_id}")
    assert response.status_code == 204

    # Confirm it's gone
    response = client.get(f"/api/v1/books/{book_id}")
    assert response.status_code == 404