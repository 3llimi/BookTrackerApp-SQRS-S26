import httpx
import pytest
from fastapi import HTTPException

from src.services import openlibrary_service


class MockResponse:
    def __init__(
        self,
        json_data=None,
        *,
        json_side_effect=None,
        raise_for_status_exc=None,
    ):
        self._json_data = json_data
        self._json_side_effect = json_side_effect
        self._raise_for_status_exc = raise_for_status_exc

    def raise_for_status(self):
        if self._raise_for_status_exc:
            raise self._raise_for_status_exc

    def json(self):
        if self._json_side_effect:
            raise self._json_side_effect
        return self._json_data


def test_search_books_success(monkeypatch):
    fake_response = {
        "docs": [
            {
                "title": "Dune",
                "author_name": ["Frank Herbert"],
                "isbn": ["9780441013593"],
                "cover_i": 12345,
                "first_publish_year": 1965,
            }
        ]
    }

    def fake_get(url, params=None, timeout=None):
        return MockResponse(json_data=fake_response)

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    results = openlibrary_service.search_books("dune")

    assert len(results) == 1
    assert results[0]["title"] == "Dune"
    assert results[0]["author"] == "Frank Herbert"
    assert results[0]["isbn"] == "9780441013593"
    assert results[0]["first_publish_year"] == 1965
    assert "covers.openlibrary.org" in results[0]["cover_url"]


def test_search_books_empty_results(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return MockResponse(json_data={"docs": []})

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    results = openlibrary_service.search_books("unknown")

    assert results == []


def test_search_books_missing_optional_fields(monkeypatch):
    fake_response = {
        "docs": [
            {
                "title": "Some Book",
            }
        ]
    }

    def fake_get(url, params=None, timeout=None):
        return MockResponse(json_data=fake_response)

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    results = openlibrary_service.search_books("something")

    assert len(results) == 1
    assert results[0]["title"] == "Some Book"
    assert results[0]["author"] is None
    assert results[0]["isbn"] is None
    assert results[0]["cover_url"] is None
    assert results[0]["first_publish_year"] is None


def test_get_book_by_isbn_success(monkeypatch):
    fake_response = {
        "title": "Dune",
        "number_of_pages": 412,
        "covers": [12345],
    }

    def fake_get(url, params=None, timeout=None):
        return MockResponse(json_data=fake_response)

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    result = openlibrary_service.get_book_by_isbn("9780441013593")

    assert result["title"] == "Dune"
    assert result["isbn"] == "9780441013593"
    assert result["total_pages"] == 412
    assert result["author"] is None
    assert result["genre"] is None
    assert "covers.openlibrary.org" in result["cover_url"]


def test_timeout_raises_503(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        openlibrary_service.search_books("dune")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Open Library request timed out"


def test_connection_error_raises_503(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise httpx.ConnectError("connection failed")

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        openlibrary_service.search_books("dune")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Could not connect to Open Library"


def test_malformed_json_raises_502(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return MockResponse(json_side_effect=ValueError("bad json"))

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        openlibrary_service.search_books("dune")

    assert exc.value.status_code == 502
    assert exc.value.detail == "Open Library returned malformed data"


def test_upstream_http_error_raises_503(monkeypatch):
    request = httpx.Request("GET", openlibrary_service.SEARCH_URL)
    response = httpx.Response(500, request=request)
    http_error = httpx.HTTPStatusError(
        "server error",
        request=request,
        response=response,
    )

    def fake_get(url, params=None, timeout=None):
        return MockResponse(raise_for_status_exc=http_error)

    monkeypatch.setattr(openlibrary_service.httpx, "get", fake_get)

    with pytest.raises(HTTPException) as exc:
        openlibrary_service.search_books("dune")

    assert exc.value.status_code == 503
    assert exc.value.detail == "Open Library returned an error"