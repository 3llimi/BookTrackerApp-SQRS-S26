from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from src.database import get_db
from src.schemas import BookCreate, BookUpdate, BookOut
from src.services import book_service, search_service
from src.services.auth_service import get_current_user
from src.models import User
from typing import Optional

router = APIRouter(prefix="/books", tags=["books"])


# POST /api/v1/books
@router.post(
    "/",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create book",
    description="Create a book record for the authenticated user.",
)
def create_book(
    data: BookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new book owned by the authenticated user."""
    return book_service.create_book(db, data, user_id=current_user.id)


# GET /api/v1/books
@router.get(
    "/",
    response_model=List[BookOut],
    summary="List and search books",
    description=(
        "List the authenticated user's books with optional filters, sorting, "
        "and pagination."
    ),
)
def list_books(
    title: Optional[str] = None,  # was only limit/offset before
    author: Optional[str] = None,
    genre: Optional[str] = None,
    status: Optional[str] = None,
    sort: str = "created_at",
    order: str = "desc",
    limit: int = 10,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's books, filtered and sorted by query parameters."""
    return search_service.search_books(
        db=db,
        user_id=current_user.id,
        q=title,  # title param maps to q search
        author=author,
        genre=genre,
        status=status,
        sort=sort,
        order=order,
        limit=limit,
        offset=offset,
    )


# GET /api/v1/books/{id}
@router.get(
    "/{book_id}",
    response_model=BookOut,
    summary="Get book by ID",
    description=(
        "Retrieve a single book (including nested progress) owned by the "
        "authenticated user."
    ),
)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get one book by ID for the authenticated user."""
    return book_service.get_book(db, book_id, user_id=current_user.id)


# PUT /api/v1/books/{id}
@router.put(
    "/{book_id}",
    response_model=BookOut,
    summary="Update book",
    description=(
        "Update editable fields of a user-owned book and return the updated "
        "record."
    ),
)
def update_book(
    book_id: int,
    data: BookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing book by ID for the authenticated user."""
    return book_service.update_book(db, book_id, data, user_id=current_user.id)


# DELETE /api/v1/books/{id}
@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete book",
    description="Delete a user-owned book and its related progress record.",
)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a book by ID for the authenticated user."""
    book_service.delete_book(db, book_id, user_id=current_user.id)
