from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from src.database import get_db
from src.schemas import ProgressCreate, ProgressUpdate, ProgressOut
from src.services import progress_service
from src.services.auth_service import get_current_user
from src.models import User

router = APIRouter(prefix="/books", tags=["progress"])


# POST /api/v1/books/{id}/progress
@router.post(
    "/{book_id}/progress",
    response_model=ProgressOut,
    status_code=status.HTTP_201_CREATED,
)
def create_progress(
    book_id: int,
    data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return progress_service.create_progress(db, book_id, data, user_id=current_user.id)


# GET /api/v1/books/{id}/progress
@router.get("/{book_id}/progress", response_model=ProgressOut)
def get_progress(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return progress_service.get_progress(db, book_id, user_id=current_user.id)


# PATCH /api/v1/books/{id}/progress
@router.patch("/{book_id}/progress", response_model=ProgressOut)
def update_progress(
    book_id: int,
    data: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return progress_service.update_progress(db, book_id, data, user_id=current_user.id)
