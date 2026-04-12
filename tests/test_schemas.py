from datetime import datetime

import pytest
from pydantic import ValidationError

from src.schemas import BookCreate, BookUpdate, BookOut, ProgressCreate, ProgressOut

# ── BookCreate ────────────────────────────────────────────────


def test_book_create_valid():
    book = BookCreate(title="Dune", author="Frank Herbert")
    assert book.title == "Dune"
    assert book.author == "Frank Herbert"
    assert book.isbn is None


def test_book_create_missing_required_fields():
    with pytest.raises(ValidationError):  # title and author are required
        BookCreate(title="Dune")  # missing author → should fail


# ── BookUpdate ────────────────────────────────────────────────


def test_book_update_all_optional():
    update = BookUpdate()
    assert update.title is None
    assert update.author is None


def test_book_update_partial():
    update = BookUpdate(title="New Title")
    assert update.title == "New Title"
    assert update.author is None


# ── ProgressCreate ────────────────────────────────────────────


def test_progress_create_valid():
    p = ProgressCreate(status="reading", current_page=50)
    assert p.status == "reading"
    assert p.current_page == 50
    assert p.rating is None


# ── ProgressOut (ORM mode) ────────────────────────────────────


def test_progress_out_from_orm():
    # Simulate what SQLAlchemy would return as an object
    class FakeProgressORM:
        id = 1
        status = "reading"
        current_page = 50
        rating = None
        notes = None
        updated_at = datetime(2024, 1, 1)

    p = ProgressOut.model_validate(FakeProgressORM())
    assert p.id == 1
    assert p.status == "reading"


# ── BookOut with nested ProgressOut ───────────────────────────


def test_book_out_with_nested_progress():
    class FakeProgressORM:
        id = 1
        status = "completed"
        current_page = 300
        rating = 5
        notes = "Great book"
        updated_at = datetime(2024, 1, 1)

    class FakeBookORM:
        id = 1
        title = "Dune"
        author = "Frank Herbert"
        isbn = "1234567890"
        genre = "Sci-Fi"
        total_pages = 300
        cover_url = None
        created_at = datetime(2024, 1, 1)
        progress = FakeProgressORM()  # nested ORM object

    book = BookOut.model_validate(FakeBookORM())
    assert book.title == "Dune"
    assert book.progress.status == "completed"
    assert book.progress.rating == 5


def test_book_create_negative_total_pages_fails():
    with pytest.raises(ValidationError):
        BookCreate(title="Dune", author="Frank Herbert", total_pages=-1)


def test_book_update_negative_total_pages_fails():
    with pytest.raises(ValidationError):
        BookUpdate(total_pages=-1)


def test_progress_create_negative_current_page_fails():
    with pytest.raises(ValidationError):
        ProgressCreate(status="reading", current_page=-1)


def test_progress_create_invalid_status_fails():
    with pytest.raises(ValidationError):
        ProgressCreate(status="paused", current_page=10)
