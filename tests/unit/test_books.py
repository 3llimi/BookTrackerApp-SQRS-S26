import pytest
from uuid import uuid4
from fastapi import HTTPException

from src.models import Book, Progress
from src.schemas import BookCreate, BookUpdate
from src.services import book_service
from src.services.auth_service import create_user


def make_user(db_session, email=None):
    if email is None:
        email = f"reader-{uuid4().hex[:8]}@test.com"

    return create_user(
        db_session,
        username=email.split("@")[0],
        email=email,
        password="password123",
    )


def test_create_book_success(db_session):
    user = make_user(db_session)
    data = BookCreate(
        title="Dune",
        author="Frank Herbert",
        isbn="9780441013593",
        genre="Sci-Fi",
        total_pages=412,
    )

    book = book_service.create_book(db_session, data, user_id=user.id)

    assert book.id is not None
    assert book.user_id == user.id
    assert book.title == "Dune"
    assert book.author == "Frank Herbert"
    assert book.isbn == "9780441013593"

    stored = db_session.query(Book).filter(Book.id == book.id).first()
    assert stored is not None
    assert stored.title == "Dune"
    assert stored.user_id == user.id


def test_create_book_duplicate_isbn_same_user_raises_409(db_session):
    user = make_user(db_session)
    first = BookCreate(title="Dune", author="Frank Herbert", isbn="DUP-123")
    second = BookCreate(title="Dune Messiah", author="Frank Herbert", isbn="DUP-123")

    book_service.create_book(db_session, first, user_id=user.id)

    with pytest.raises(HTTPException) as exc:
        book_service.create_book(db_session, second, user_id=user.id)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Book with this ISBN already exists"


def test_get_book_success(db_session):
    user = make_user(db_session)
    data = BookCreate(title="Dune", author="Frank Herbert")
    created = book_service.create_book(db_session, data, user_id=user.id)

    book = book_service.get_book(db_session, created.id, user_id=user.id)

    assert book.id == created.id
    assert book.title == "Dune"
    assert book.author == "Frank Herbert"


def test_get_book_not_found_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        book_service.get_book(db_session, 9999, user_id=user.id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"


def test_update_book_partial_success(db_session):
    user = make_user(db_session)
    created = book_service.create_book(
        db_session,
        BookCreate(title="Old Title", author="Original Author", genre="Sci-Fi"),
        user_id=user.id,
    )

    updated = book_service.update_book(
        db_session,
        created.id,
        BookUpdate(title="New Title"),
        user_id=user.id,
    )

    assert updated.id == created.id
    assert updated.title == "New Title"
    assert updated.author == "Original Author"
    assert updated.genre == "Sci-Fi"


def test_update_book_not_found_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        book_service.update_book(
            db_session,
            9999,
            BookUpdate(title="Does not matter"),
            user_id=user.id,
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"


def test_delete_book_success(db_session):
    user = make_user(db_session)
    created = book_service.create_book(
        db_session,
        BookCreate(title="To Delete", author="Someone"),
        user_id=user.id,
    )

    book_service.delete_book(db_session, created.id, user_id=user.id)

    deleted = db_session.query(Book).filter(Book.id == created.id).first()
    assert deleted is None


def test_delete_book_cascade_deletes_progress(db_session):
    user = make_user(db_session)
    created = book_service.create_book(
        db_session,
        BookCreate(title="Tracked Book", author="Reader", total_pages=300),
        user_id=user.id,
    )

    progress = Progress(
        book_id=created.id,
        status="reading",
        current_page=120,
        rating=5,
        notes="Great so far",
    )
    db_session.add(progress)
    db_session.commit()

    assert db_session.query(Progress).filter(Progress.book_id == created.id).first() is not None

    book_service.delete_book(db_session, created.id, user_id=user.id)

    deleted_book = db_session.query(Book).filter(Book.id == created.id).first()
    deleted_progress = db_session.query(Progress).filter(Progress.book_id == created.id).first()

    assert deleted_book is None
    assert deleted_progress is None


def test_delete_book_not_found_raises_404(db_session):
    user = make_user(db_session)

    with pytest.raises(HTTPException) as exc:
        book_service.delete_book(db_session, 9999, user_id=user.id)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Book not found"