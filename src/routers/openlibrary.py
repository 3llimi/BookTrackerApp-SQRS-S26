from fastapi import APIRouter, Depends
from src.services import openlibrary_service
from src.services.auth_service import get_current_user
from src.models import User

router = APIRouter(prefix="/openlibrary", tags=["openlibrary"])


@router.get("/search")
def search_openlibrary(q: str, current_user: User = Depends(get_current_user)):
    return openlibrary_service.search_books(q)


@router.get("/book/{isbn}")
def get_book_by_isbn(isbn: str, current_user: User = Depends(get_current_user)):
    return openlibrary_service.get_book_by_isbn(isbn)
