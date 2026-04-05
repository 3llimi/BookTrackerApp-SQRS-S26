from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.models import Book
from src.schemas import BookCreate, BookUpdate


def create_book(db: Session, data: BookCreate, user_id: int) -> Book:
    """Create a new book for the user.

    Raises 409 if a book with the same ISBN already exists for the user.
    """
    # 409 if ISBN already exists
    if data.isbn:
        existing_book = (
            db.query(Book).filter_by(isbn=data.isbn, user_id=user_id).first()
        )
        if existing_book:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Book with this ISBN already exists",
            )

    book = Book(**data.model_dump(), user_id=user_id)
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def get_books(db: Session, user_id: int, limit: int = 10, offset: int = 0):
    """Get a list of books for the user."""
    return (
        db.query(Book)
        .filter(Book.user_id == user_id)  # only this user's books
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_book(db: Session, book_id: int, user_id: int) -> Book:
    """Get a single book by ID for the user. Raises 404 if not found."""
    book = db.query(Book).filter(Book.id == book_id, Book.user_id == user_id).first()
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
        )
    return book


def update_book(db: Session, book_id: int, data: BookUpdate, user_id: int) -> Book:
    book = get_book(db, book_id, user_id)  # reuse get_book cuz it already handles 404
    # only update fields that were actually sent (not None)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, book_id: int, user_id: int):
    book = get_book(db, book_id, user_id)  # reuse get_book cuz it already handles 404
    db.delete(book)
    db.commit()
