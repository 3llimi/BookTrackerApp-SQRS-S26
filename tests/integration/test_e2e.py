from uuid import uuid4


def _unique_email(prefix: str = "e2e") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@test.com"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_end_to_end_user_flow(client):
    email = _unique_email()
    password = "password123"

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
    headers = _auth_headers(token)

    create_book_response = client.post(
        "/api/v1/books/",
        json={
            "title": "The Pragmatic Programmer",
            "author": "Andrew Hunt",
            "genre": "Programming",
            "total_pages": 352,
        },
        headers=headers,
    )
    assert create_book_response.status_code == 201
    book_id = create_book_response.json()["id"]

    create_progress_response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": 100, "rating": 4},
        headers=headers,
    )
    assert create_progress_response.status_code == 201

    update_progress_response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": 352, "rating": 5, "notes": "Excellent read"},
        headers=headers,
    )
    assert update_progress_response.status_code == 200
    assert update_progress_response.json()["status"] == "completed"

    list_books_response = client.get(
        "/api/v1/books/?title=Pragmatic",
        headers=headers,
    )
    assert list_books_response.status_code == 200
    books = list_books_response.json()
    assert len(books) == 1
    assert books[0]["title"] == "The Pragmatic Programmer"
    assert books[0]["progress"]["status"] == "completed"

    delete_response = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert delete_response.status_code == 204

    get_deleted_response = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_deleted_response.status_code == 404
