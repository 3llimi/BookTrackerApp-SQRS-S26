from fastapi import APIRouter, Depends
from src.services import openlibrary_service
from src.services.auth_service import get_current_user
from src.models import User

router = APIRouter(prefix="/openlibrary", tags=["openlibrary"])


@router.get(
    "/search",
    summary="Search Open Library",
    description="Search Open Library by free-text query and return mapped book suggestions.",
)
def search_openlibrary(q: str, current_user: User = Depends(get_current_user)):
    """Search Open Library for books by query text."""
    return openlibrary_service.search_books(q)


@router.get(
    "/book/{isbn}",
    summary="Get Open Library book by ISBN",
    description="Fetch and map a single Open Library book result by ISBN.",
)
def get_book_by_isbn(isbn: str, current_user: User = Depends(get_current_user)):
    """Fetch Open Library metadata for one ISBN."""
    return openlibrary_service.get_book_by_isbn(isbn)
