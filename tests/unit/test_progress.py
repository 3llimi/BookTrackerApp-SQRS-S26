import pytest
from uuid import uuid4
from fastapi import HTTPException
from pydantic import ValidationError

from src.schemas import BookCreate, ProgressCreate, ProgressUpdate
from src.services import book_service, progress_service
from src.services.auth_service import create_user


def make_user(db_session, email=None):
    if email is None:
        email = f"progress-user-{uuid4().hex[:8]}@test.com"

    return create_user(
        db_session,
        username=email.split("@")[0],
        email=email,
        password="password123",
    )


def make_book(db_session, user_id, total_pages=300):
    return book_service.create_book(
        db_session,
        BookCreate(
            title="Test Book",
            author="Test Author",
            total_pages=total_pages,
        ),
        user_id=user_id,
    )


def test_create_progress_success(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id, total_pages=300)

    progress = progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=50, rating=4),
        user_id=user.id,
    )

    assert progress.id is not None
    assert progress.book_id == book.id
    assert progress.status == "reading"
    assert progress.current_page == 50
    assert progress.rating == 4


def test_create_progress_duplicate_raises_409(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=10),
        user_id=user.id,
    )

    with pytest.raises(HTTPException) as exc:
        progress_service.create_progress(
            db_session,
            book.id,
            ProgressCreate(status="reading", current_page=20),
            user_id=user.id,
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Progress already exists for this book"


def test_create_progress_missing_book_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        progress_service.create_progress(
            db_session,
            9999,
            ProgressCreate(status="reading", current_page=20),
            user_id=user.id,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"


def test_create_progress_current_page_exceeds_total_pages_raises_422(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id, total_pages=200)

    with pytest.raises(HTTPException) as exc:
        progress_service.create_progress(
            db_session,
            book.id,
            ProgressCreate(status="reading", current_page=999),
            user_id=user.id,
        )

    assert exc.value.status_code == 422
    assert "cannot exceed" in exc.value.detail


def test_get_progress_success(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    created = progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=40),
        user_id=user.id,
    )

    progress = progress_service.get_progress(db_session, book.id, user_id=user.id)

    assert progress.id == created.id
    assert progress.status == "reading"
    assert progress.current_page == 40


def test_get_progress_missing_book_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        progress_service.get_progress(db_session, 9999, user_id=user.id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"


def test_get_progress_without_record_raises_404(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    with pytest.raises(HTTPException) as exc:
        progress_service.get_progress(db_session, book.id, user_id=user.id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "No progress record found for this book"


def test_update_progress_partial_success(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=50, rating=3),
        user_id=user.id,
    )

    updated = progress_service.update_progress(
        db_session,
        book.id,
        ProgressUpdate(current_page=100),
        user_id=user.id,
    )

    assert updated.current_page == 100
    assert updated.status == "reading"
    assert updated.rating == 3


@pytest.mark.parametrize(
    "new_page,expected_status",
    [
        (0, "not_started"),
        (100, "reading"),
        (300, "completed"),
    ],
)
def test_update_progress_status_transitions(db_session, new_page, expected_status):
    user = make_user(db_session)
    book = make_book(db_session, user.id, total_pages=300)

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=50),
        user_id=user.id,
    )

    updated = progress_service.update_progress(
        db_session,
        book.id,
        ProgressUpdate(current_page=new_page),
        user_id=user.id,
    )

    assert updated.current_page == new_page
    assert updated.status == expected_status


def test_update_progress_invalid_rating_raises_422(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=20),
        user_id=user.id,
    )

    with pytest.raises(HTTPException) as exc:
        progress_service.update_progress(
            db_session,
            book.id,
            ProgressUpdate(rating=6),
            user_id=user.id,
        )

    assert exc.value.status_code == 422
    assert exc.value.detail == "Rating must be between 1 and 5"


def test_update_progress_current_page_exceeds_total_pages_raises_422(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id, total_pages=200)

    progress_service.create_progress(
        db_session,
        book.id,
        ProgressCreate(status="reading", current_page=50),
        user_id=user.id,
    )

    with pytest.raises(HTTPException) as exc:
        progress_service.update_progress(
            db_session,
            book.id,
            ProgressUpdate(current_page=999),
            user_id=user.id,
        )

    assert exc.value.status_code == 422
    assert "cannot exceed" in exc.value.detail


def test_update_progress_missing_book_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        progress_service.update_progress(
            db_session,
            9999,
            ProgressUpdate(current_page=10),
            user_id=user.id,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"


def test_update_progress_without_record_raises_404(db_session):
    user = make_user(db_session)
    book = make_book(db_session, user.id)

    with pytest.raises(HTTPException) as exc:
        progress_service.update_progress(
            db_session,
            book.id,
            ProgressUpdate(current_page=10),
            user_id=user.id,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "No progress record found for this book"


def test_create_progress_invalid_status_fails_schema_validation():
    with pytest.raises(ValidationError) as exc:
        ProgressCreate(status="paused", current_page=10)

    assert "Input should be 'not_started', 'reading' or 'completed'" in str(exc.value)


def test_create_progress_negative_current_page_fails_schema_validation():
    with pytest.raises(ValidationError) as exc:
        ProgressCreate(status="reading", current_page=-1)

    assert "greater than or equal to 0" in str(exc.value)


def test_update_progress_invalid_status_fails_schema_validation():
    with pytest.raises(ValidationError) as exc:
        ProgressUpdate(status="paused")

    assert "Input should be 'not_started', 'reading' or 'completed'" in str(exc.value)
