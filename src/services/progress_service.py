from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.models import Progress, Book
from src.schemas import ProgressCreate, ProgressUpdate


# helper: get book or 404
def _get_book(db: Session, book_id: int, user_id: int) -> Book:
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


# CREATE
def create_progress(
    db: Session, book_id: int, data: ProgressCreate, user_id: int
) -> Progress:
    # Ensure the book exists and belongs to the user
    book = _get_book(db, book_id, user_id)

    # 409 if progress already exists for this book
    if book.progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Progress already exists for this book",
        )

    # validate pages_read <= total_pages
    if data.pages_read and book.total_pages:
        if data.pages_read > book.total_pages:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"pages_read ({data.pages_read}) cannot exceed "
                    f"total_pages ({book.total_pages})"
                ),
            )

    # validate rating 1-5
    if data.rating is not None:
        if not (1 <= data.rating <= 5):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Rating must be between 1 and 5",
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
def update_progress(
    db: Session, book_id: int, data: ProgressUpdate, user_id: int
) -> Progress:
    book = _get_book(db, book_id, user_id)
    progress = book.progress

    if not progress:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No progress record found for this book",
        )

    # get only the fields the user actually sent
    updates = data.model_dump(exclude_unset=True)

    new_pages = updates.get("pages_read", progress.pages_read)
    if book.total_pages and new_pages > book.total_pages:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"pages_read ({new_pages}) cannot exceed "
                f"total_pages ({book.total_pages})"
            ),
        )

    new_rating = updates.get("rating")
    if new_rating is not None and not (1 <= new_rating <= 5):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Rating must be between 1 and 5",
        )

    # apply updates
    for field, value in updates.items():
        setattr(progress, field, value)

    # auto-set status to finished when pages_read == total_pages
    if book.total_pages and progress.pages_read == book.total_pages:
        progress.status = "finished"

    db.commit()
    db.refresh(progress)
    return progress
