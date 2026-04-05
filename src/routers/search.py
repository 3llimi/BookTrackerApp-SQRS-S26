from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database import get_db
from src.schemas import BookOut
from src.services import search_service

router = APIRouter(prefix="/books", tags=["search"])


@router.get("/search", response_model=List[BookOut])
def search_books(
    q: Optional[str] = None,           # partial match on title + author
    genre: Optional[str] = None,       # exact match
    author: Optional[str] = None,      # partial match
    status: Optional[str] = None,      # want_to_read / reading / finished
    sort: str = "created_at",          # default sort
    order: str = "desc",               # default order
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    return search_service.search_books(
        db=db,
        user_id=1,          # hardcoded for now
        q=q,
        genre=genre,
        author=author,
        status=status,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset
    )