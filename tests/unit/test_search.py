import pytest
from uuid import uuid4
from hypothesis import HealthCheck, given, settings, strategies as st
from src.schemas import BookCreate, ProgressCreate
from src.services import book_service, progress_service, search_service
from src.services.auth_service import create_user


def make_user(db_session, email=None):
    if email is None:
        email = f"search-user-{uuid4().hex[:8]}@test.com"

    return create_user(
        db_session,
        username=email.split("@")[0],
        email=email,
        password="password123",
    )


def create_book_with_progress(
    db_session,
    user_id,
    title,
    author,
    genre,
    total_pages,
    current_page,
    rating,
):
    book = book_service.create_book(
        db_session,
        BookCreate(
            title=title,
            author=author,
            genre=genre,
            total_pages=total_pages,
        ),
        user_id=user_id,
    )

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(
            status="reading",
            current_page=current_page,
            rating=rating,
        ),
        user_id=user_id,
    )

    return book


def seed_books(db_session, user_id):
    create_book_with_progress(
        db_session, user_id, "Dune", "Frank Herbert", "Sci-Fi", 300, 300, 5
    )
    create_book_with_progress(
        db_session, user_id, "Dune Messiah", "Frank Herbert", "Sci-Fi", 280, 120, 4
    )
    create_book_with_progress(
        db_session, user_id, "The Hobbit", "J.R.R. Tolkien", "Fantasy", 320, 0, 3
    )
    create_book_with_progress(
        db_session, user_id, "Clean Code", "Robert Martin", "Programming", 450, 200, 2
    )
    create_book_with_progress(
        db_session, user_id, "Foundation", "Isaac Asimov", "Sci-Fi", 255, 255, 1
    )


def test_search_by_q_returns_matching_titles(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q="dune")

    titles = [book.title for book in results]
    assert len(results) == 2
    assert "Dune" in titles
    assert "Dune Messiah" in titles


def test_search_by_q_can_match_author(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q="tolkien")

    titles = [book.title for book in results]
    assert len(results) == 1
    assert titles == ["The Hobbit"]


def test_filter_by_author_partial_match(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, author="herbert")

    titles = [book.title for book in results]
    assert len(results) == 2
    assert "Dune" in titles
    assert "Dune Messiah" in titles


def test_filter_by_genre_case_insensitive(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, genre="fantasy")

    titles = [book.title for book in results]
    assert len(results) == 1
    assert titles == ["The Hobbit"]


def test_filter_by_status(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, status="completed")

    titles = [book.title for book in results]
    assert len(results) == 2
    assert "Dune" in titles
    assert "Foundation" in titles


@pytest.mark.parametrize(
    "q,genre,expected_titles",
    [
        ("dune", "Sci-Fi", ["Dune", "Dune Messiah"]),
        ("foundation", "Sci-Fi", ["Foundation"]),
    ],
)
def test_q_and_genre_combination(db_session, q, genre, expected_titles):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q=q, genre=genre)

    titles = [book.title for book in results]
    assert titles == expected_titles


@pytest.mark.parametrize(
    "q,status,expected_titles",
    [
        ("dune", "reading", ["Dune Messiah"]),
        ("dune", "completed", ["Dune"]),
    ],
)
def test_q_and_status_combination(db_session, q, status, expected_titles):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q=q, status=status)

    titles = [book.title for book in results]
    assert titles == expected_titles


@pytest.mark.parametrize(
    "sort_field,order,expected_titles",
    [
        (
            "title",
            "asc",
            ["Clean Code", "Dune", "Dune Messiah", "Foundation", "The Hobbit"],
        ),
        (
            "rating",
            "desc",
            ["Dune", "Dune Messiah", "The Hobbit", "Clean Code", "Foundation"],
        ),
    ],
)
def test_sort_and_order(db_session, sort_field, order, expected_titles):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(
        db_session,
        user.id,
        sort=sort_field,
        order=order,
    )

    titles = [book.title for book in results]
    assert titles == expected_titles


def test_invalid_sort_field_raises_422(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    with pytest.raises(Exception) as exc:
        search_service.search_books(db_session, user.id, sort="invalid_field")

    assert exc.value.status_code == 422
    assert "Invalid sort field" in exc.value.detail


def test_empty_string_query_returns_all_results(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q="")

    assert len(results) == 5


@pytest.mark.parametrize("query", ["!@#$%^&*()", "[]{}<>", "C++??"])
def test_special_characters_do_not_crash(db_session, query):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q=query)

    assert isinstance(results, list)


def test_sql_injection_like_input_returns_no_results_and_does_not_crash(db_session):
    user = make_user(db_session)
    seed_books(db_session, user.id)

    results = search_service.search_books(db_session, user.id, q="' OR 1=1 --")

    assert results == []


def test_search_is_scoped_to_current_user(db_session):
    user_a = make_user(db_session)
    user_b = make_user(db_session)

    seed_books(db_session, user_a.id)
    create_book_with_progress(
        db_session,
        user_b.id,
        "Private Book",
        "Secret Author",
        "Hidden",
        100,
        50,
        5,
    )

    results = search_service.search_books(db_session, user_a.id, q="private")

    assert results == []


def ensure_hypothesis_seeded_user(db_session):
    from src.models import Book, User

    user = db_session.query(User).filter(User.email == "hypothesis@test.com").first()
    if user is None:
        user = make_user(db_session, "hypothesis@test.com")

    user_books = db_session.query(Book).filter(Book.user_id == user.id).count()
    if user_books == 0:
        seed_books(db_session, user.id)

    return user


@given(st.text())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_hypothesis_q_never_crashes_and_returns_list(db_session, q):
    user = ensure_hypothesis_seeded_user(db_session)

    results = search_service.search_books(db_session, user.id, q=q)

    assert isinstance(results, list)


@given(st.text())
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_hypothesis_author_never_crashes_and_returns_list(db_session, author):
    user = ensure_hypothesis_seeded_user(db_session)

    results = search_service.search_books(db_session, user.id, author=author)

    assert isinstance(results, list)


@given(st.from_regex(r"\d{8,12}", fullmatch=True))
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_hypothesis_non_matching_numeric_query_returns_empty_list(db_session, q):
    user = ensure_hypothesis_seeded_user(db_session)

    results = search_service.search_books(db_session, user.id, q=q)

    assert results == []
