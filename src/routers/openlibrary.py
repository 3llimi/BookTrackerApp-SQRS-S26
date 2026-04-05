from fastapi import APIRouter
from src.services import openlibrary_service

router = APIRouter(prefix="/openlibrary", tags=["openlibrary"])


# GET /api/v1/openlibrary/search?q=
@router.get("/search")
def search_openlibrary(q: str):
    return openlibrary_service.search_books(q)


# GET /api/v1/openlibrary/book/{isbn}
@router.get("/book/{isbn}")
def get_book_by_isbn(isbn: str):
    return openlibrary_service.get_book_by_isbn(isbn)