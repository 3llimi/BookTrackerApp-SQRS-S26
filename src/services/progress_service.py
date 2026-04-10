from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.models import Progress, Book


# helper: get book or 404
def _get_book(db: Session, book_id: int, user_id: int) -> Book:
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


def _validate_current_page(current_page: int | None, total_pages: int | None) -> None:
    if current_page and total_pages and current_page > total_pages:
        detail = (
            f"current_page ({current_page}) cannot exceed "
            f"total_pages ({total_pages})"
        )
        raise HTTPException(status_code=422, detail=detail)


def _validate_rating(rating: int | None) -> None:
    if rating is not None and not (1 <= rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")


def _sync_status_with_page(progress: Progress, total_pages: int | None) -> None:
    current_page = int(progress.current_page or 0)

    if total_pages and current_page == total_pages and current_page > 0:
        progress.status = "completed"
    elif current_page > 0:
        progress.status = "reading"


# CREATE
def create_progress(db, book_id, data, user_id):
    book = _get_book(db, book_id, user_id)

    if book.progress:
        raise HTTPException(
            status_code=409, detail="Progress already exists for this book"
        )

    _validate_current_page(data.current_page, book.total_pages)
    _validate_rating(data.rating)

    progress = Progress(**data.model_dump(), book_id=book_id)
    _sync_status_with_page(progress, book.total_pages)
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


# GET
def get_progress(db: Session, book_id: int, user_id: int) -> Progress:
    book = _get_book(db, book_id, user_id)

    if not book.progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress record found for this book",
        )
    return book.progress


# PATCH
def update_progress(db, book_id, data, user_id):
    book = _get_book(db, book_id, user_id)
    progress = book.progress

    if not progress:
        raise HTTPException(
            status_code=404, detail="No progress record found for this book"
        )

    updates = data.model_dump(exclude_unset=True)

    new_page = updates.get("current_page", progress.current_page)
    _validate_current_page(new_page, book.total_pages)
    _validate_rating(updates.get("rating"))

    for field, value in updates.items():
        setattr(progress, field, value)

    _sync_status_with_page(progress, book.total_pages)

    db.commit()
    db.refresh(progress)
    return progress
