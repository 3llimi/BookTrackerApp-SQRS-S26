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


# CREATE
def create_progress(db, book_id, data, user_id):
    book = _get_book(db, book_id, user_id)

    if book.progress:
        raise HTTPException(
            status_code=409, detail="Progress already exists for this book"
        )

    if data.current_page and book.total_pages:
        if data.current_page > book.total_pages:
            detail = (
                f"current_page ({data.current_page}) cannot exceed "
                f"total_pages ({book.total_pages})"
            )
            raise HTTPException(
                status_code=422,
                detail=detail,
            )

    if data.rating is not None:
        if not (1 <= data.rating <= 5):
            raise HTTPException(
                status_code=422, detail="Rating must be between 1 and 5"
            )

    progress = Progress(**data.model_dump(), book_id=book_id)
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

    # validate current_page <= total_pages
    new_page = updates.get("current_page", progress.current_page)  # was pages_read
    if book.total_pages and new_page > book.total_pages:
        detail = (
            f"current_page ({new_page}) cannot exceed "
            f"total_pages ({book.total_pages})"
        )
        raise HTTPException(
            status_code=422,
            detail=detail,
        )

    # validate rating
    new_rating = updates.get("rating")
    if new_rating is not None and not (1 <= new_rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be between 1 and 5")

    for field, value in updates.items():
        setattr(progress, field, value)

    # auto-set status to completed when current_page == total_pages
    if book.total_pages and progress.current_page == book.total_pages:
        progress.status = "completed"  # was "finished"
    elif progress.current_page == 0:
        progress.status = "not_started"  # was "want_to_read"
    elif progress.current_page < book.total_pages:
        progress.status = "reading"

    db.commit()
    db.refresh(progress)
    return progress
