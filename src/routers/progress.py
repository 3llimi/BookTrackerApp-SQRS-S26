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
    summary="Create progress",
    description="Create a progress record for a user-owned book.",
)
def create_progress(
    book_id: int,
    data: ProgressCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create reading progress for a specific book."""
    return progress_service.create_progress(db, book_id, data, user_id=current_user.id)


# GET /api/v1/books/{id}/progress
@router.get(
    "/{book_id}/progress",
    response_model=ProgressOut,
    summary="Get progress",
    description="Get the progress record for a user-owned book.",
)
def get_progress(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the reading progress for one book."""
    return progress_service.get_progress(db, book_id, user_id=current_user.id)


# PATCH /api/v1/books/{id}/progress
@router.patch(
    "/{book_id}/progress",
    response_model=ProgressOut,
    summary="Update progress",
    description=(
        "Partially update reading progress and derived status for a "
        "user-owned book."
    ),
)
def update_progress(
    book_id: int,
    data: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Patch reading progress values for one book."""
    return progress_service.update_progress(
        db, book_id, data, user_id=current_user.id
    )
