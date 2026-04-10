import httpx
import re
from fastapi import HTTPException

SEARCH_URL = "https://openlibrary.org/search.json"
ISBN_URL = "https://openlibrary.org/isbn/{isbn}.json"
WORK_URL = "https://openlibrary.org{work_key}.json"
COVER_URL = "https://covers.openlibrary.org/b/id/{cover_i}-M.jpg"
TIMEOUT = 5.0
SEARCH_FIELDS = (
    "title,author_name,isbn,cover_i,first_publish_year,subject,number_of_pages_median"
)


def _parse_total_pages(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float):
        if value.is_integer() and value >= 0:
            return int(value)
        return None

    if isinstance(value, str):
        match = re.search(r"\d+", value.replace(",", ""))
        if not match:
            return None
        pages = int(match.group(0))
        return pages if pages >= 0 else None

    return None


def _make_request(
    url: str, params: dict = None, *, follow_redirects: bool = False
) -> dict:
    """
    Single helper for all external HTTP calls.
    Wraps every possible failure into the correct HTTP error.
    """
    try:
        # Keep compatibility with simple monkeypatched fakes in unit tests
        # that do not accept follow_redirects as a keyword argument.
        if follow_redirects:
            try:
                response = httpx.get(
                    url,
                    params=params,
                    timeout=TIMEOUT,
                    follow_redirects=True,
                )
            except TypeError as exc:
                if "follow_redirects" not in str(exc):
                    raise
                response = httpx.get(
                    url,
                    params=params,
                    timeout=TIMEOUT,
                )
        else:
            response = httpx.get(
                url,
                params=params,
                timeout=TIMEOUT,
            )
        response.raise_for_status()  # raises on 4xx/5xx from Open Library
        return response.json()

    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="Open Library request timed out")
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Could not connect to Open Library")
    except ValueError:
        # response.json() failed — malformed JSON
        raise HTTPException(
            status_code=502, detail="Open Library returned malformed data"
        )
    except httpx.HTTPStatusError:
        raise HTTPException(status_code=503, detail="Open Library returned an error")


def _extract_genre(subjects: list | None) -> str | None:
    if not subjects:
        return None

    for item in subjects:
        if isinstance(item, str):
            value = item.strip()
            if value:
                return value
        elif isinstance(item, dict):
            value = str(item.get("name") or item.get("subject") or "").strip()
            if value:
                return value
    return None


def _extract_first_work_key(works: list | None) -> str | None:
    if not works:
        return None

    for item in works:
        if isinstance(item, dict):
            key = str(item.get("key") or "").strip()
            if key.startswith("/works/"):
                return key
        elif isinstance(item, str):
            key = item.strip()
            if key.startswith("/works/"):
                return key

    return None


# SEARCH BOOKS


def search_books(q: str) -> list:
    data = _make_request(
        SEARCH_URL,
        params={"q": q, "limit": 10, "fields": SEARCH_FIELDS},
    )

    results = []
    for doc in data.get("docs", []):
        # extract cover URL if cover_i exists
        cover_i = doc.get("cover_i")
        cover_url = COVER_URL.format(cover_i=cover_i) if cover_i else None

        # isbn is a list in Open Library — take first one if available
        isbn_list = doc.get("isbn", [])
        isbn = isbn_list[0] if isbn_list else None
        genre = _extract_genre(doc.get("subject"))
        total_pages = _parse_total_pages(doc.get("number_of_pages_median"))

        results.append(
            {
                "title": doc.get("title"),
                "author": doc.get("author_name", [None])[0],  # first author
                "isbn": isbn,
                "cover_url": cover_url,
                "first_publish_year": doc.get("first_publish_year"),
                "genre": genre,
                "total_pages": total_pages,
            }
        )

    return results


# GET BY ISBN
def get_book_by_isbn(isbn: str) -> dict:
    data = _make_request(ISBN_URL.format(isbn=isbn), follow_redirects=True)

    # shape it like BookCreate so frontend can pre-fill the form
    title = data.get("title")
    covers = data.get("covers", [])
    cover_url = COVER_URL.format(cover_i=covers[0]) if covers else None

    raw_total_pages = data.get("number_of_pages")
    if raw_total_pages is None:
        raw_total_pages = data.get("pagination")
    total_pages = _parse_total_pages(raw_total_pages)
    genre = _extract_genre(data.get("subjects"))

    if not genre:
        work_key = _extract_first_work_key(data.get("works"))
        if work_key:
            try:
                work_data = _make_request(
                    WORK_URL.format(work_key=work_key), follow_redirects=True
                )
                genre = _extract_genre(work_data.get("subjects"))
            except HTTPException:
                # keep original response if work lookup fails
                genre = genre

    return {
        "title": title,
        "author": None,  # ISBN endpoint doesn't include author name directly
        "isbn": isbn,
        "cover_url": cover_url,
        "total_pages": total_pages,
        "genre": genre,
    }
