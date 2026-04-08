from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx
import streamlit as st

API_BASE = "http://localhost:8000/api/v1"
PAGE_TITLE = "Book Tracker"
LOGIN_PAGE = "pages/0_login.py"
MY_BOOKS_PAGE = "pages/1_my_books.py"
ADD_BOOK_PAGE = "pages/2_add_book.py"
SEARCH_PAGE = "pages/3_search.py"
PROGRESS_PAGE = "pages/4_progress.py"

NAV_ITEMS = [
    ("Login", LOGIN_PAGE),
    ("My Books", MY_BOOKS_PAGE),
    ("Add Book", ADD_BOOK_PAGE),
    ("Search", SEARCH_PAGE),
    ("Progress", PROGRESS_PAGE),
]

API_TO_UI_STATUS = {
    "not_started": "want_to_read",
    "reading": "reading",
    "completed": "finished",
}

UI_TO_API_STATUS = {
    "want_to_read": "not_started",
    "reading": "reading",
    "finished": "completed",
}

STATUS_LABELS = {
    "not_started": "Want to Read",
    "reading": "Reading",
    "completed": "Finished",
}

STATUS_EMOJI = {
    "not_started": "To Read",
    "reading": "Reading",
    "completed": "Done",
}


def configure_page(page_name: str) -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    init_session_state()
    st.session_state["current_page_name"] = page_name


def init_session_state() -> None:
    defaults = {
        "token": None,
        "auth_notice": None,
        "page_notice": None,
        "book_id": None,
        "editing_book_id": None,
        "selected_book_id": None,
        "book_form_loaded_id": None,
        "openlibrary_results": [],
        "openlibrary_query": "",
        "openlibrary_last_query": "",
        "search_last_value": "",
        "progress_loaded_book_id": None,
        "progress_snapshot": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def set_notice(level: str, text: str) -> None:
    st.session_state["page_notice"] = {"level": level, "text": text}


def show_notice() -> None:
    notice = st.session_state.pop("page_notice", None)
    if not notice:
        return

    level = notice.get("level", "info")
    text = notice.get("text", "")
    if not text:
        return

    if level == "success":
        st.success(text)
    elif level == "warning":
        st.warning(text)
    elif level == "error":
        st.error(text)
    else:
        st.info(text)


def render_sidebar(current_page: str, show_logout: bool = True) -> None:
    with st.sidebar:
        st.title("Book Tracker")
        st.caption("Simple personal reading workspace")

        nav_targets = NAV_ITEMS[1:] if st.session_state.get("token") else NAV_ITEMS[:1]

        for label, page in nav_targets:
            button_type = "primary" if page == current_page else "secondary"
            if st.button(label, key=f"nav_{label.lower().replace(' ', '_')}", width="stretch", type=button_type):
                go_to_page(page)

        if show_logout and st.session_state.get("token"):
            st.divider()
            if st.button("Logout", width="stretch", type="secondary"):
                logout_user("You have been logged out.")


def render_hero(title: str, subtitle: str, kicker: str = "") -> None:
    if kicker:
        st.caption(kicker)
    st.title(title)
    st.write(subtitle)
    st.divider()


def render_empty_state(title: str, body: str) -> None:
    st.info(f"{title}\n\n{body}")


def go_to_page(page: str) -> None:
    st.switch_page(page)
    st.stop()


def require_auth() -> None:
    if not st.session_state.get("token"):
        st.session_state["auth_notice"] = "Please log in to continue."
        go_to_page(LOGIN_PAGE)


def logout_user(message: str | None = None) -> None:
    for key in (
        "token",
        "book_id",
        "editing_book_id",
        "selected_book_id",
        "book_form_loaded_id",
        "progress_loaded_book_id",
        "progress_snapshot",
    ):
        st.session_state[key] = None

    st.session_state["auth_notice"] = message
    go_to_page(LOGIN_PAGE)


def api_request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    auth_required: bool = True,
    timeout: float = 10.0,
    expect_json: bool = True,
) -> Any:
    headers: dict[str, str] = {}

    if auth_required:
        token = st.session_state.get("token")
        if not token:
            st.session_state["auth_notice"] = "Please log in to continue."
            go_to_page(LOGIN_PAGE)
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = httpx.request(
            method=method.upper(),
            url=f"{API_BASE}{path}",
            params=params,
            json=json,
            headers=headers,
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        raise RuntimeError("The API is taking too long to respond. Please try again.") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Could not reach the API. Make sure the backend is running on localhost:8000."
        ) from exc

    if response.status_code == 401 and auth_required:
        logout_user("Your session expired. Please log in again.")

    if response.is_error:
        detail = extract_error_detail(response)
        raise RuntimeError(detail)

    if not expect_json or response.status_code == 204:
        return None

    return response.json()


def extract_error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text.strip() or "The request failed."

    detail = data.get("detail", "The request failed.")
    if isinstance(detail, list):
        return "; ".join(str(item) for item in detail)
    if isinstance(detail, dict):
        return ", ".join(f"{key}: {value}" for key, value in detail.items())
    return str(detail)


def cover_image_source(title: str, cover_url: str | None = None) -> str:
    if cover_url:
        return cover_url

    short_title = (title or "Book")[:40]
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="420" height="620" viewBox="0 0 420 620">
        <rect width="420" height="620" rx="36" fill="#2d4f61"/>
        <rect x="36" y="36" width="348" height="548" rx="28" fill="#496d80"/>
        <text x="210" y="260" text-anchor="middle" font-family="sans-serif" font-size="28" fill="#ffffff">Book Tracker</text>
        <text x="210" y="320" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#ffffff">{short_title}</text>
    </svg>
    """
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def get_book_status(book: dict[str, Any]) -> str:
    progress = book.get("progress") or {}
    return progress.get("status") or "not_started"


def get_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, "Want to Read")


def get_status_text(status: str) -> str:
    return f"{STATUS_EMOJI.get(status, 'Status')}: {get_status_label(status)}"


def get_progress_value(book: dict[str, Any], field: str, default: Any = None) -> Any:
    progress = book.get("progress") or {}
    return progress.get(field, default)


def format_rating(value: int) -> str:
    if value <= 0:
        return "No rating"
    filled = chr(9733) * value
    empty = chr(9734) * (5 - value)
    return f"{filled}{empty}"


def build_book_options(books: list[dict[str, Any]]) -> list[tuple[str, int]]:
    return [(f"{book['title']} by {book['author']}", int(book["id"])) for book in books]
