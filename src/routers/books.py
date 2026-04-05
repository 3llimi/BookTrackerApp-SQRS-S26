from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.schemas import BookCreate, BookUpdate, BookOut
from src.services import book_service
from src.services.auth_service import get_current_user
from src.models import User

router = APIRouter(prefix="/books", tags=["books"])


# POST /api/v1/books
@router.post("/", response_model=BookOut, status_code=status.HTTP_201_CREATED)
def create_book(
    data: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.create_book(db, data, user_id=current_user.id)


# GET /api/v1/books
@router.get("/", response_model=List[BookOut])
def list_books(
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_books(
        db, user_id=current_user.id, limit=limit, offset=offset
    )


# GET /api/v1/books/{id}
@router.get("/{book_id}", response_model=BookOut)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.get_book(db, book_id, user_id=current_user.id)


# PUT /api/v1/books/{id}
@router.put("/{book_id}", response_model=BookOut)
def update_book(
    book_id: int,
    data: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return book_service.update_book(db, book_id, data, user_id=current_user.id)


# DELETE /api/v1/books/{id}
@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    book_service.delete_book(db, book_id, user_id=current_user.id)
