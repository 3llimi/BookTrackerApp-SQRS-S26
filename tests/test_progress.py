from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


# helper to create a book to use in tests
def create_test_book(total_pages=300):
    response = client.post("/api/v1/books/", json={
        "title": "Test Book",
        "author": "Test Author",
        "total_pages": total_pages
    })
    return response.json()["id"]


def test_create_progress():
    book_id = create_test_book()
    response = client.post(f"/api/v1/books/{book_id}/progress", json={
        "status": "reading",
        "pages_read": 50
    })
    assert response.status_code == 201
    assert response.json()["status"] == "reading"
    assert response.json()["pages_read"] == 50


def test_create_progress_409_if_already_exists():
    book_id = create_test_book()
    client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})

    # second time → 409
    response = client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})
    assert response.status_code == 409


def test_create_progress_book_not_found():
    response = client.post("/api/v1/books/9999/progress", json={"status": "reading"})
    assert response.status_code == 404


def test_get_progress():
    book_id = create_test_book()
    client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})

    response = client.get(f"/api/v1/books/{book_id}/progress")
    assert response.status_code == 200
    assert response.json()["status"] == "reading"


def test_get_progress_404_if_none():
    book_id = create_test_book()
    response = client.get(f"/api/v1/books/{book_id}/progress")
    assert response.status_code == 404


def test_patch_progress_partial():
    book_id = create_test_book()
    client.post(f"/api/v1/books/{book_id}/progress", json={
        "status": "reading",
        "pages_read": 50
    })

    # only update pages_read
    response = client.patch(f"/api/v1/books/{book_id}/progress", json={
        "pages_read": 100
    })
    assert response.status_code == 200
    assert response.json()["pages_read"] == 100
    assert response.json()["status"] == "reading"   # untouched


def test_patch_progress_pages_exceed_total():
    book_id = create_test_book(total_pages=200)
    client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})

    response = client.patch(f"/api/v1/books/{book_id}/progress", json={
        "pages_read": 999   # exceeds total_pages=200
    })
    assert response.status_code == 422


def test_patch_progress_invalid_rating():
    book_id = create_test_book()
    client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})

    response = client.patch(f"/api/v1/books/{book_id}/progress", json={
        "rating": 6     # must be 1-5
    })
    assert response.status_code == 422


def test_auto_finish_when_pages_complete():
    book_id = create_test_book(total_pages=300)
    client.post(f"/api/v1/books/{book_id}/progress", json={"status": "reading"})

    # set pages_read == total_pages → should auto-set status to finished
    response = client.patch(f"/api/v1/books/{book_id}/progress", json={
        "pages_read": 300
    })
    assert response.status_code == 200
    assert response.json()["status"] == "finished"   # auto-set!