import httpx
from fastapi import HTTPException

SEARCH_URL = "https://openlibrary.org/search.json"
ISBN_URL   = "https://openlibrary.org/isbn/{isbn}.json"
COVER_URL  = "https://covers.openlibrary.org/b/id/{cover_i}-M.jpg"
TIMEOUT    = 5.0

def _make_request(url: str, params: dict = None) -> dict:
    """
    Single helper for all external HTTP calls.
    Wraps every possible failure into the correct HTTP error.
    """
    try:
        response = httpx.get(url, params=params, timeout=TIMEOUT)
        response.raise_for_status()   # raises on 4xx/5xx from Open Library
        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=503,
            detail="Open Library request timed out"
        )
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to Open Library"
        )
    except ValueError:
        # response.json() failed — malformed JSON
        raise HTTPException(
            status_code=502,
            detail="Open Library returned malformed data"
        )
    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=503,
            detail="Open Library returned an error"
        )


# SEARCH BOOKS

def search_books(q: str) -> list:
    data = _make_request(SEARCH_URL, params={"q": q, "limit": 10})

    results = []
    for doc in data.get("docs", []):
        # extract cover URL if cover_i exists
        cover_i = doc.get("cover_i")
        cover_url = COVER_URL.format(cover_i=cover_i) if cover_i else None

        # isbn is a list in Open Library — take first one if available
        isbn_list = doc.get("isbn", [])
        isbn = isbn_list[0] if isbn_list else None

        results.append({
            "title":             doc.get("title"),
            "author":            doc.get("author_name", [None])[0],  # first author
            "isbn":              isbn,
            "cover_url":         cover_url,
            "first_publish_year": doc.get("first_publish_year"),
        })

    return results


# GET BY ISBN
def get_book_by_isbn(isbn: str) -> dict:
    data = _make_request(ISBN_URL.format(isbn=isbn))

    # shape it like BookCreate so frontend can pre-fill the form
    title  = data.get("title")
    covers = data.get("covers", [])
    cover_url = COVER_URL.format(cover_i=covers[0]) if covers else None

    # number_of_pages or pagination field
    total_pages = data.get("number_of_pages") or data.get("pagination")

    authors = data.get("authors", [])

    return {
        "title":       title,
        "author":      None,        # ISBN endpoint doesn't include author name directly
        "isbn":        isbn,       
        "cover_url":   cover_url,
        "total_pages": total_pages,
        "genre":       None,    
    }