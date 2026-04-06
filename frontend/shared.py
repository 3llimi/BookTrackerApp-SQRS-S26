from __future__ import annotations

from html import escape
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

STATUS_CLASSES = {
    "not_started": "want",
    "reading": "reading",
    "completed": "finished",
}

SORT_OPTIONS = {
    "Newest": ("created_at", "desc"),
    "Oldest": ("created_at", "asc"),
    "Title A-Z": ("title", "asc"),
    "Title Z-A": ("title", "desc"),
    "Author A-Z": ("author", "asc"),
    "Author Z-A": ("author", "desc"),
    "Top Rated": ("rating", "desc"),
}


def configure_page(page_name: str) -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    init_session_state()
    inject_theme()
    st.session_state["current_page_name"] = page_name


def init_session_state() -> None:
    defaults = {
        "token": None,
        "auth_notice": None,
        "book_id": None,
        "editing_book_id": None,
        "selected_book_id": None,
        "book_form_loaded_id": None,
        "openlibrary_results": [],
        "openlibrary_query": "",
        "openlibrary_last_query": "",
        "search_last_query": "",
        "search_last_value": "",
        "progress_loaded_book_id": None,
        "progress_snapshot": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def inject_theme() -> None:
    st.markdown(
        """
        <style>
            :root {
                --bt-cream: #f5f2ec;
                --bt-paper: rgba(255, 253, 250, 0.94);
                --bt-ink: #17313b;
                --bt-muted: #4e6771;
                --bt-line: rgba(24, 49, 58, 0.08);
                --bt-teal: #186f68;
                --bt-teal-deep: #124f4b;
                --bt-gold: #c98b2e;
                --bt-sky: #dff0eb;
                --bt-peach: #fff1dd;
                --bt-danger: #b44d41;
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, #fff0cf 0%, rgba(255, 240, 207, 0.12) 34%),
                    radial-gradient(circle at top right, #d7ece6 0%, rgba(215, 236, 230, 0.18) 28%),
                    linear-gradient(180deg, #f8f5ef 0%, #f1eee7 100%);
                color: var(--bt-ink);
                font-family: "Trebuchet MS", "Segoe UI", sans-serif;
            }

            .block-container {
                padding-top: 1.2rem;
                padding-bottom: 2rem;
                max-width: 1280px;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #19343e 0%, #122730 100%);
                border-right: 1px solid rgba(255, 255, 255, 0.06);
            }

            [data-testid="stSidebarNav"],
            [data-testid="stSidebarNavSeparator"] {
                display: none !important;
            }

            [data-testid="stSidebar"] .stMarkdown,
            [data-testid="stSidebar"] .stMarkdown p,
            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] .stCaption {
                color: #f7f6f1 !important;
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3,
            [data-testid="stSidebar"] h4,
            [data-testid="stSidebar"] h5,
            [data-testid="stSidebar"] h6,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
            [data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {
                color: #f7f6f1 !important;
            }

            .bt-brand {
                padding: 0.9rem 0 1rem 0;
            }

            .bt-brand small {
                display: block;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: rgba(247, 246, 241, 0.65);
                margin-bottom: 0.3rem;
            }

            .bt-brand strong {
                display: block;
                font-size: 1.45rem;
                font-family: "Palatino Linotype", Georgia, serif;
                line-height: 1.1;
            }

            .bt-hero {
                background:
                    linear-gradient(135deg, rgba(255, 250, 241, 0.96) 0%, rgba(225, 240, 236, 0.94) 100%);
                border: 1px solid rgba(18, 115, 107, 0.12);
                border-radius: 26px;
                padding: 1.35rem 1.5rem;
                box-shadow: 0 18px 42px rgba(24, 49, 58, 0.08);
                animation: bt-fade-up 0.45s ease-out;
                margin-bottom: 1rem;
            }

            .bt-kicker {
                display: inline-block;
                font-size: 0.78rem;
                text-transform: uppercase;
                letter-spacing: 0.12em;
                color: var(--bt-teal);
                margin-bottom: 0.4rem;
                font-weight: 700;
            }

            .bt-hero h1, .bt-hero h2 {
                margin: 0;
                font-family: "Palatino Linotype", Georgia, serif;
                color: var(--bt-ink);
            }

            .bt-hero p {
                margin: 0.55rem 0 0 0;
                color: #2f4751;
                max-width: 58rem;
                line-height: 1.55;
            }

            .bt-card {
                background: var(--bt-paper);
                border: 1px solid var(--bt-line);
                border-radius: 24px;
                padding: 1rem;
                box-shadow: 0 14px 30px rgba(24, 49, 58, 0.06);
                animation: bt-fade-up 0.45s ease-out;
            }

            .bt-card-title {
                margin-top: 0.8rem;
                font-size: 1.08rem;
                font-weight: 700;
                color: var(--bt-ink);
                line-height: 1.3;
            }

            .bt-card-meta {
                color: #34505a;
                margin-top: 0.15rem;
                margin-bottom: 0.75rem;
            }

            .bt-status {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.28rem 0.72rem;
                font-size: 0.82rem;
                font-weight: 700;
                margin: 0.2rem 0 0.9rem 0;
            }

            .bt-status.want {
                background: #fff0d4;
                color: #8c6419;
            }

            .bt-status.reading {
                background: #dff5ef;
                color: #126a61;
            }

            .bt-status.finished {
                background: #dfe8ff;
                color: #3657a0;
            }

            .bt-row {
                background: rgba(255, 252, 247, 0.94);
                border: 1px solid var(--bt-line);
                border-radius: 18px;
                padding: 0.7rem 0.9rem;
                margin-bottom: 0.65rem;
                box-shadow: 0 10px 22px rgba(24, 49, 58, 0.04);
                animation: bt-fade-up 0.35s ease-out;
            }

            .bt-row strong {
                color: var(--bt-ink);
                font-size: 1rem;
            }

            .bt-row small {
                color: #304b54;
            }

            .bt-empty {
                background: rgba(255, 252, 247, 0.88);
                border: 1px dashed rgba(18, 115, 107, 0.26);
                border-radius: 24px;
                padding: 2rem 1.4rem;
                text-align: center;
                color: #2f4a53;
            }

            .bt-cover-placeholder {
                height: 260px;
                border-radius: 18px;
                border: 1px solid var(--bt-line);
                overflow: hidden;
            }

            div[data-testid="stMetric"] {
                background: rgba(255, 252, 247, 0.94);
                border: 1px solid var(--bt-line);
                border-radius: 22px;
                padding: 0.7rem 0.95rem;
                box-shadow: 0 12px 28px rgba(24, 49, 58, 0.05);
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 999px;
                border: 1px solid transparent;
                background: linear-gradient(135deg, var(--bt-teal) 0%, var(--bt-teal-deep) 100%);
                color: white;
                font-weight: 700;
                min-height: 2.35rem;
                box-shadow: 0 10px 22px rgba(18, 115, 107, 0.18);
                transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
            }

            .stFormSubmitButton > button {
                border-radius: 999px;
                border: 1px solid transparent;
                background: linear-gradient(135deg, var(--bt-teal) 0%, var(--bt-teal-deep) 100%);
                color: #ffffff !important;
                font-weight: 700;
                min-height: 2.35rem;
            }

            .stButton > button:hover,
            .stDownloadButton > button:hover,
            .stFormSubmitButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 14px 28px rgba(18, 115, 107, 0.24);
            }

            .stButton > button[kind="secondary"] {
                background: rgba(255, 255, 255, 0.96);
                color: var(--bt-ink);
                border-color: rgba(24, 49, 58, 0.22);
                box-shadow: none;
            }

            [data-testid="stSidebar"] .stButton > button {
                background: linear-gradient(135deg, #355e6e 0%, #254754 100%);
                color: #f7f6f1 !important;
                border: 1px solid rgba(255, 255, 255, 0.18);
                box-shadow: none;
            }

            [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
                background: #f5f3ee;
                color: #1f3942 !important;
                border: 1px solid rgba(30, 56, 65, 0.2);
            }

            .stTextInput input,
            .stTextArea textarea,
            .stSelectbox div[data-baseweb="select"] > div,
            .stNumberInput input,
            .stDateInput input {
                border-radius: 7px;
                background: rgba(255, 255, 255, 0.92);
                color: #17303a !important;
                border: 1px solid rgba(24, 49, 58, 0.22) !important;
            }

            .stTextInput input:focus,
            .stTextArea textarea:focus,
            .stSelectbox div[data-baseweb="select"] > div:focus-within,
            .stNumberInput input:focus {
                border-color: rgba(24, 111, 104, 0.55) !important;
                box-shadow: 0 0 0 1px rgba(24, 111, 104, 0.25) !important;
            }

            .stTextInput input::placeholder,
            .stTextArea textarea::placeholder {
                color: #5c7380 !important;
                opacity: 1;
            }

            [data-testid="stWidgetLabel"] p,
            [data-testid="stWidgetLabel"] span,
            .stCaption,
            p,
            h1, h2, h3, h4 {
                color: #17303a !important;
            }

            .stTabs [data-baseweb="tab"] p {
                color: #22404a !important;
                font-weight: 700;
            }

            .stTabs [aria-selected="true"] {
                background: #e8f3ef !important;
                border: 1px solid rgba(18, 115, 107, 0.35) !important;
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.45rem;
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px;
                padding: 0.45rem 0.9rem;
                background: rgba(255, 255, 255, 0.6);
            }

            .stExpander {
                border-radius: 20px;
                overflow: hidden;
                border: 1px solid var(--bt-line);
                background: rgba(255, 252, 247, 0.78);
            }

            .stAlert {
                border-radius: 16px;
            }

            @keyframes bt-fade-up {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(current_page: str, show_logout: bool = True) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="bt-brand">
                <small>Streamlit Frontend</small>
                <strong>Book Tracker</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("token"):
            nav_targets = NAV_ITEMS[1:]
        else:
            nav_targets = NAV_ITEMS[:1]

        for label, page in nav_targets:
            button_type = "primary" if page == current_page else "secondary"
            if st.button(
                label,
                key=f"nav_{label.lower().replace(' ', '_')}",
                width="stretch",
                type=button_type,
            ):
                go_to_page(page)

        if show_logout and st.session_state.get("token"):
            st.divider()
            if st.button("Logout", width="stretch", type="secondary"):
                logout_user("You have been logged out.")


def render_hero(title: str, subtitle: str, kicker: str = "Book Tracker") -> None:
    st.markdown(
        f"""
        <section class="bt-hero">
            <span class="bt-kicker">{escape(kicker)}</span>
            <h1>{escape(title)}</h1>
            <p>{escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="bt-empty">
            <h3>{escape(title)}</h3>
            <p>{escape(body)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


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

    short_title = escape((title or "Book")[:40])
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="420" height="620" viewBox="0 0 420 620">
        <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#143642"/>
                <stop offset="55%" stop-color="#12736b"/>
                <stop offset="100%" stop-color="#d6982f"/>
            </linearGradient>
        </defs>
        <rect width="420" height="620" rx="36" fill="url(#bg)"/>
        <rect x="36" y="36" width="348" height="548" rx="28" fill="rgba(255,255,255,0.12)"/>
        <text x="210" y="240" text-anchor="middle" font-family="Georgia, serif" font-size="34" fill="#fff6ea">Book Tracker</text>
        <text x="210" y="305" text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="22" fill="#f7f1e7">{short_title}</text>
    </svg>
    """
    return f"data:image/svg+xml;utf8,{quote(svg)}"


def get_book_status(book: dict[str, Any]) -> str:
    progress = book.get("progress") or {}
    return progress.get("status") or "not_started"


def get_status_label(status: str) -> str:
    return STATUS_LABELS.get(status, "Want to Read")


def get_status_badge(status: str) -> str:
    label = get_status_label(status)
    css_class = STATUS_CLASSES.get(status, "want")
    return f'<span class="bt-status {css_class}">{escape(label)}</span>'


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
    return [
        (f"{book['title']} by {book['author']}", int(book["id"]))
        for book in books
    ]
