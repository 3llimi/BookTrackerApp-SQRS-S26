from sqlalchemy import or_, asc, desc
from fastapi import HTTPException
from src.models import Book, Progress

# valid sort fields, anything else returns 422
VALID_SORT_FIELDS = {"title", "author", "created_at", "rating"}


def search_books(
    db,
    user_id,
    q=None,
    genre=None,
    author=None,
    status=None,
    sort="created_at",
    order="desc",
    limit=10,
    offset=0,
):

    if sort not in VALID_SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"Invalid sort field '{sort}'")

    query = db.query(Book).filter(Book.user_id == user_id)

    if q:
        term = f"%{q.lower()}%"
        query = query.filter(or_(Book.title.ilike(term), Book.author.ilike(term)))

    if genre:
        query = query.filter(
            Book.genre.ilike(f"%{genre}%")
        )  # case-insensitive per spec

    if author:
        query = query.filter(Book.author.ilike(f"%{author.lower()}%"))

    if status:
        query = query.join(Progress).filter(Progress.status == status)

    if sort == "rating":
        if not status:
            query = query.join(Progress)
        sort_column = Progress.rating
    else:
        sort_column = getattr(Book, sort)

    query = query.order_by(asc(sort_column) if order == "asc" else desc(sort_column))

    return query.offset(offset).limit(limit).all()
