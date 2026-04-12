from uuid import uuid4


def register_and_login(client, email=None, password="password123"):
    if email is None:
        email = f"search-{uuid4().hex[:8]}@test.com"

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


def create_book(client, headers, title, author, genre, total_pages=300):
    response = client.post(
        "/api/v1/books/",
        json={
            "title": title,
            "author": author,
            "genre": genre,
            "total_pages": total_pages,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def add_progress(client, headers, book_id, current_page, rating=5):
    response = client.post(
        f"/api/v1/books/{book_id}/progress",
        json={"status": "reading", "current_page": current_page, "rating": rating},
        headers=headers,
    )
    assert response.status_code == 201
    return response


def seed_books(client, headers):
    dune = create_book(client, headers, "Dune", "Frank Herbert", "Sci-Fi", 300)
    dune_messiah = create_book(
        client, headers, "Dune Messiah", "Frank Herbert", "Sci-Fi", 280
    )
    hobbit = create_book(
        client, headers, "The Hobbit", "J.R.R. Tolkien", "Fantasy", 320
    )
    clean_code = create_book(
        client, headers, "Clean Code", "Robert Martin", "Programming", 450
    )
    foundation = create_book(
        client, headers, "Foundation", "Isaac Asimov", "Sci-Fi", 255
    )

    add_progress(client, headers, dune, 300, rating=5)  # completed
    add_progress(client, headers, dune_messiah, 120, rating=4)  # reading
    add_progress(client, headers, hobbit, 0, rating=3)  # not_started
    add_progress(client, headers, clean_code, 200, rating=2)  # reading
    add_progress(client, headers, foundation, 255, rating=1)  # completed


def test_filter_by_title_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?title=dune", headers=headers)

    assert response.status_code == 200
    data = response.json()
    titles = [book["title"] for book in data]

    assert len(data) == 2
    assert "Dune" in titles
    assert "Dune Messiah" in titles


def test_filter_by_author_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?author=tolkien", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "The Hobbit"


def test_filter_by_genre_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?genre=Sci-Fi", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 3
    assert all(book["genre"] == "Sci-Fi" for book in data)


def test_filter_by_status_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?status=completed", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert all(book["progress"]["status"] == "completed" for book in data)


def test_title_and_genre_combination_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?title=dune&genre=Sci-Fi", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert all("dune" in book["title"].lower() for book in data)


def test_title_and_status_combination_returns_exact_count(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?title=dune&status=reading", headers=headers)

    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Dune Messiah"
    assert data[0]["progress"]["status"] == "reading"


def test_sort_by_title_asc(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?sort=title&order=asc", headers=headers)

    assert response.status_code == 200
    titles = [book["title"] for book in response.json()]
    assert titles == ["Clean Code", "Dune", "Dune Messiah", "Foundation", "The Hobbit"]


def test_invalid_sort_field_returns_422(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?sort=invalid_field", headers=headers)

    assert response.status_code == 422
    assert "Invalid sort field" in response.json()["detail"]


def test_empty_title_returns_all_books(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?title=", headers=headers)

    assert response.status_code == 200
    assert len(response.json()) == 5


def test_sql_injection_like_input_returns_zero_results(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?title=' OR 1=1 --", headers=headers)

    assert response.status_code == 200
    assert response.json() == []


# case-insensitive genre
def test_filter_by_genre_is_case_insensitive(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get("/api/v1/books?genre=fantasy", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "The Hobbit"


# user scoping
def test_search_is_scoped_to_current_user(client):
    headers_a = register_and_login(client, email="search-owner@test.com")
    headers_b = register_and_login(client, email="search-other@test.com")

    seed_books(client, headers_a)
    create_book(client, headers_b, "Private Book", "Secret Author", "Hidden", 100)

    response = client.get("/api/v1/books?title=private", headers=headers_a)

    assert response.status_code == 200
    assert response.json() == []


# pagination on filtered results
def test_search_respects_limit_and_offset(client):
    headers = register_and_login(client)
    seed_books(client, headers)

    response = client.get(
        "/api/v1/books?sort=title&order=asc&limit=2&offset=1",
        headers=headers,
    )

    assert response.status_code == 200
    titles = [book["title"] for book in response.json()]
    assert titles == ["Dune", "Dune Messiah"]
