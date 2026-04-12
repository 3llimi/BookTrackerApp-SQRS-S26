from uuid import uuid4


def _unique_email(prefix: str = "e2e") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@test.com"


def _register_and_login(client, email: str, password: str = "password123") -> dict:
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


def _create_book(
    client,
    headers: dict,
    *,
    title: str,
    author: str,
    genre: str | None = None,
    total_pages: int | None = None,
):
    payload = {
        "title": title,
        "author": author,
    }
    if genre is not None:
        payload["genre"] = genre
    if total_pages is not None:
        payload["total_pages"] = total_pages

    response = client.post("/api/v1/books/", json=payload, headers=headers)
    assert response.status_code == 201
    return response


def _create_progress(
    client,
    headers: dict,
    book_id: int,
    *,
    status: str = "not_started",
    current_page: int = 0,
    rating: int | None = None,
):
    payload = {
        "status": status,
        "current_page": current_page,
    }
    if rating is not None:
        payload["rating"] = rating

    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    return response


def test_end_to_end_full_crud_lifecycle(client):
    email = _unique_email("e2e-crud")
    headers = _register_and_login(client, email)

    create_book_response = _create_book(
        client,
        headers,
        title="The Pragmatic Programmer",
        author="Andrew Hunt",
        genre="Programming",
        total_pages=352,
    )
    book_id = create_book_response.json()["id"]

    get_book_response = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_book_response.status_code == 200
    book_data = get_book_response.json()
    assert book_data["title"] == "The Pragmatic Programmer"
    assert book_data["author"] == "Andrew Hunt"
    assert book_data["progress"] is None

    create_progress_response = _create_progress(
        client,
        headers,
        book_id,
        status="not_started",
        current_page=0,
        rating=4,
    )
    assert create_progress_response.json()["status"] == "not_started"

    update_progress_response = client.patch(
        f"/api/v1/books/{book_id}/progress",
        json={"current_page": 352, "rating": 5, "notes": "Excellent read"},
        headers=headers,
    )
    assert update_progress_response.status_code == 200
    updated_progress = update_progress_response.json()
    assert updated_progress["current_page"] == 352
    assert updated_progress["status"] == "completed"
    assert updated_progress["rating"] == 5
    assert updated_progress["notes"] == "Excellent read"

    get_updated_book_response = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_updated_book_response.status_code == 200
    updated_book = get_updated_book_response.json()
    assert updated_book["progress"] is not None
    assert updated_book["progress"]["status"] == "completed"
    assert updated_book["progress"]["current_page"] == 352
    assert updated_book["progress_percentage"] == 100.0

    delete_response = client.delete(f"/api/v1/books/{book_id}", headers=headers)
    assert delete_response.status_code == 204

    get_deleted_response = client.get(f"/api/v1/books/{book_id}", headers=headers)
    assert get_deleted_response.status_code == 404
    assert get_deleted_response.json()["detail"] == "Book not found"


def test_end_to_end_multi_user_isolation(client):
    headers_a = _register_and_login(client, _unique_email("e2e-user-a"))
    headers_b = _register_and_login(client, _unique_email("e2e-user-b"))

    create_response = _create_book(
        client,
        headers_a,
        title="Private Book",
        author="Owner Only",
        genre="Secret",
        total_pages=120,
    )
    book_id = create_response.json()["id"]

    get_as_other_user = client.get(f"/api/v1/books/{book_id}", headers=headers_b)
    assert get_as_other_user.status_code == 404
    assert get_as_other_user.json()["detail"] == "Book not found"

    list_as_other_user = client.get("/api/v1/books/", headers=headers_b)
    assert list_as_other_user.status_code == 200
    titles = [book["title"] for book in list_as_other_user.json()]
    assert "Private Book" not in titles


def test_end_to_end_search_and_filter(client):
    headers = _register_and_login(client, _unique_email("e2e-search"))

    dune = _create_book(
        client,
        headers,
        title="Dune",
        author="Frank Herbert",
        genre="Sci-Fi",
        total_pages=300,
    ).json()["id"]

    dune_messiah = _create_book(
        client,
        headers,
        title="Dune Messiah",
        author="Frank Herbert",
        genre="Sci-Fi",
        total_pages=280,
    ).json()["id"]

    hobbit = _create_book(
        client,
        headers,
        title="The Hobbit",
        author="J.R.R. Tolkien",
        genre="Fantasy",
        total_pages=320,
    ).json()["id"]

    clean_code = _create_book(
        client,
        headers,
        title="Clean Code",
        author="Robert Martin",
        genre="Programming",
        total_pages=450,
    ).json()["id"]

    foundation = _create_book(
        client,
        headers,
        title="Foundation",
        author="Isaac Asimov",
        genre="Sci-Fi",
        total_pages=255,
    ).json()["id"]

    _create_progress(
        client, headers, dune, status="reading", current_page=300, rating=5
    )
    _create_progress(
        client,
        headers,
        dune_messiah,
        status="reading",
        current_page=120,
        rating=4,
    )
    _create_progress(
        client, headers, hobbit, status="not_started", current_page=0, rating=3
    )
    _create_progress(
        client,
        headers,
        clean_code,
        status="reading",
        current_page=200,
        rating=2,
    )
    _create_progress(
        client,
        headers,
        foundation,
        status="reading",
        current_page=255,
        rating=1,
    )

    title_response = client.get("/api/v1/books?title=dune", headers=headers)
    assert title_response.status_code == 200
    title_results = title_response.json()
    assert len(title_results) == 2
    title_values = [book["title"] for book in title_results]
    assert "Dune" in title_values
    assert "Dune Messiah" in title_values

    genre_response = client.get("/api/v1/books?genre=Sci-Fi", headers=headers)
    assert genre_response.status_code == 200
    genre_results = genre_response.json()
    assert len(genre_results) == 3
    assert all(book["genre"] == "Sci-Fi" for book in genre_results)

    status_response = client.get("/api/v1/books?status=completed", headers=headers)
    assert status_response.status_code == 200
    status_results = status_response.json()
    assert len(status_results) == 2
    completed_titles = {book["title"] for book in status_results}
    assert completed_titles == {"Dune", "Foundation"}
    assert all(book["progress"]["status"] == "completed" for book in status_results)
