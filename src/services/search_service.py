from sqlalchemy.orm import Session
from sqlalchemy import or_, asc, desc
from fastapi import HTTPException
from src.models import Book, Progress
from typing import Optional

# valid sort fields, anything else returns 422
VALID_SORT_FIELDS = {"title", "author", "created_at", "rating"}


def search_books(
    db: Session,
    user_id: int,
    q: Optional[str] = None,
    genre: Optional[str] = None,
    author: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    limit: int = 10,
    offset: int = 0,
):
    # validate sort field first
    if sort not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid sort field '{sort}'. Must be one of: "
                f"{', '.join(VALID_SORT_FIELDS)}"
            ),
        )
        # start with base query — always filter by current user
    query = db.query(Book).filter(Book.user_id == user_id)

    # q: partial match across title AND author
    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                Book.title.ilike(search_term),  # ilike = case-insensitive LIKE
                Book.author.ilike(search_term),
            )
        )

    # genre: exact match
    if genre:
        query = query.filter(Book.genre == genre)

    # author: partial match
    if author:
        query = query.filter(Book.author.ilike(f"%{author.lower()}%"))

    # status: filter by progress status
    # needs a join because status lives in the Progress table
    if status:
        query = query.join(Progress).filter(Progress.status == status)

    # Sorting
    if sort == "rating":
        # rating lives in Progress table so we need a join
        if not status:
            query = query.join(Progress)
        sort_column = Progress.rating
    else:
        sort_column = getattr(Book, sort)  # Book.title, Book.author, Book.created_at

    if order == "asc":
        query = query.order_by(asc(sort_column))
    else:
        query = query.order_by(desc(sort_column))

    return query.offset(offset).limit(limit).all()
