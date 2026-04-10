from __future__ import annotations

from html import escape
import os
from typing import Any
from urllib.parse import quote

import httpx
import streamlit as st

API_BASE = os.getenv("BOOKTRACKER_API_BASE", "http://localhost:8000/api/v1").rstrip("/")
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

SORT_OPTIONS = {
    "Newest": ("created_at", "desc"),
    "Oldest": ("created_at", "asc"),
    "Title A-Z": ("title", "asc"),
    "Title Z-A": ("title", "desc"),
    "Author A-Z": ("author", "asc"),
    "Author Z-A": ("author", "desc"),
    "Top Rated": ("rating", "desc"),
}

THEME_PALETTES = {
    "dark": {
        "bg": (
            "radial-gradient(circle at 85% 0%, #1e3532 0%, rgba(30, 53, 50, 0.25) "
            "28%), linear-gradient(180deg, #121518 0%, #0f1b20 48%, #172126 100%)"
        ),
        "card": "rgba(24, 31, 36, 0.92)",
        "card_border": "#36434f",
        "ink": "#e8e4d7",
        "muted": "#b8b3a2",
        "accent": "#57b29f",
        "accent_soft": "#274b46",
        "sidebar": "linear-gradient(180deg, #171f25 0%, #11171c 100%)",
        "hero": "linear-gradient(120deg, #23363d 0%, #1b2d33 50%, #213b35 100%)",
        "hero_border": "#3f5b67",
        "shadow": "rgba(2, 6, 9, 0.35)",
    },
}

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?family=Fraunces:wght@500;700&family="
    "Manrope:wght@400;500;600;700&display=swap"
)


def build_global_style(motion_enabled: bool) -> str:
    palette = THEME_PALETTES["dark"]
    transition_rule = "all 220ms ease" if motion_enabled else "none"
    lift_translate = "translateY(-2px)" if motion_enabled else "translateY(0)"
    entry_animation = "bt-fade-up 0.55s ease both" if motion_enabled else "none"

    return f"""
<style>
@import url('{GOOGLE_FONTS_URL}');

:root {{
    --bt-bg: {palette['bg']};
    --bt-card: {palette['card']};
    --bt-card-border: {palette['card_border']};
    --bt-ink: {palette['ink']};
    --bt-muted: {palette['muted']};
    --bt-accent: {palette['accent']};
    --bt-accent-soft: {palette['accent_soft']};
    --bt-danger: #b54a3d;
    --bt-sidebar: {palette['sidebar']};
    --bt-hero: {palette['hero']};
    --bt-hero-border: {palette['hero_border']};
    --bt-shadow: {palette['shadow']};
}}

html,
body,
[class*="css"],
[data-testid="stAppViewContainer"] {{
    font-family: "Manrope", "Segoe UI", sans-serif;
    color: var(--bt-ink);
}}

[data-testid="stAppViewContainer"] {{
    background: var(--bt-bg);
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

h1, h2, h3 {{
    font-family: "Fraunces", Georgia, serif;
    letter-spacing: 0.2px;
    color: var(--bt-ink);
}}

.block-container {{
    max-width: 1280px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}}

div[data-testid="stMetric"] {{
    background: var(--bt-card);
    border: 1px solid var(--bt-card-border);
    border-radius: 14px;
    padding: 0.7rem 0.9rem;
    transition: {transition_rule};
    animation: {entry_animation};
}}

div[data-testid="stMetric"]:hover {{
    transform: {lift_translate};
    box-shadow: 0 8px 20px var(--bt-shadow);
}}

.bt-hero {{
    background: var(--bt-hero);
    border: 1px solid var(--bt-hero-border);
    border-radius: 18px;
    padding: 1.1rem 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 8px 20px var(--bt-shadow);
    animation: {entry_animation};
}}

.bt-hero-kicker {{
    text-transform: uppercase;
    font-size: 0.74rem;
    letter-spacing: 0.11em;
    font-weight: 700;
    color: var(--bt-muted);
    margin-bottom: 0.25rem;
}}

.bt-hero-title {{
    font-family: "Fraunces", Georgia, serif;
    font-size: 2rem;
    line-height: 1.2;
    margin: 0;
    color: var(--bt-ink);
}}

.bt-hero-subtitle {{
    margin-top: 0.45rem;
    color: var(--bt-muted);
    font-size: 1rem;
}}

.bt-chip {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border-radius: 999px;
    padding: 0.22rem 0.62rem;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid transparent;
}}

.bt-chip-want {{
    background: rgba(209, 175, 119, 0.18);
    border-color: rgba(209, 175, 119, 0.5);
    color: #b08239;
}}

.bt-chip-reading {{
    background: var(--bt-accent-soft);
    border-color: rgba(87, 178, 159, 0.6);
    color: var(--bt-accent);
}}

.bt-chip-finished {{
    background: rgba(218, 139, 64, 0.2);
    border-color: rgba(218, 139, 64, 0.55);
    color: #d88b40;
}}

.bt-panel-note {{
    color: var(--bt-muted);
    font-size: 0.84rem;
}}

div[data-testid="stSidebar"] {{
    background: var(--bt-sidebar);
    border-right: 1px solid var(--bt-card-border);
}}

div[data-testid="stSidebar"] h1,
div[data-testid="stSidebar"] h2,
div[data-testid="stSidebar"] h3,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] span {{
    color: var(--bt-ink);
}}

.stButton > button,
.stFormSubmitButton > button {{
    transition: {transition_rule};
    min-height: 2.25rem;
    line-height: 1.15;
    white-space: normal;
    text-wrap: balance;
    padding-top: 0.38rem;
    padding-bottom: 0.38rem;
}}

.stButton > button:hover,
.stFormSubmitButton > button:hover {{
    transform: {lift_translate};
}}

@keyframes bt-fade-up {{
    from {{
        opacity: 0;
        transform: translateY(12px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}

@media (max-width: 960px) {{
    .block-container {{
        padding-left: 0.7rem;
        padding-right: 0.7rem;
    }}

    .bt-hero {{
        border-radius: 14px;
        padding: 0.9rem 0.95rem;
    }}

    .bt-hero-title {{
        font-size: 1.55rem;
    }}

    div[data-testid="stMetric"] {{
        padding: 0.55rem 0.65rem;
    }}

    .stButton > button,
    .stFormSubmitButton > button {{
        min-height: 2.15rem;
    }}
}}

@media (max-width: 680px) {{
    .bt-hero-subtitle {{
        font-size: 0.93rem;
    }}
}}
</style>
"""


STATUS_CHIP_CLASS = {
    "not_started": "bt-chip-want",
    "reading": "bt-chip-reading",
    "completed": "bt-chip-finished",
}

LAYOUT_DENSITY_OPTIONS = ["Adaptive", "Comfort", "Compact"]


def configure_page(page_name: str) -> None:
    st.set_page_config(page_title=PAGE_TITLE, page_icon="📚", layout="wide")
    init_session_state()
    inject_global_styles()
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
        "openlibrary_expanded": False,
        "openlibrary_import_notice": None,
        "openlibrary_clear_query_pending": False,
        "search_last_query": "",
        "search_last_value": "",
        "progress_loaded_book_id": None,
        "progress_snapshot": None,
        "pending_delete_book_id": None,
        "layout_density": "Adaptive",
        "motion_enabled": True,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_sidebar(current_page: str, show_logout: bool = True) -> None:
    with st.sidebar:
        st.title("Book Tracker")
        st.caption("Your Reading Companion")
        st.markdown("Track every chapter, one page at a time.")
        st.caption(
            "Organize your library, log reading progress, and keep notes in one place."
        )
        st.divider()

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
                logout_user("You have logged out successfully.")


def render_hero(title: str, subtitle: str, kicker: str = "Book Tracker") -> None:
    safe_kicker = escape(kicker)
    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    st.markdown(
        f"""
        <section class="bt-hero">
            <div class="bt-hero-kicker">{safe_kicker}</div>
            <h1 class="bt-hero-title">{safe_title}</h1>
            <p class="bt-hero-subtitle">{safe_subtitle}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str) -> None:
    st.info(f"{title}\n\n{body}")


def inject_global_styles() -> None:
    st.markdown(
        build_global_style(
            motion_enabled=bool(st.session_state.get("motion_enabled", True)),
        ),
        unsafe_allow_html=True,
    )


def get_layout_density() -> str:
    value = str(st.session_state.get("layout_density", "Adaptive"))
    if value not in set(LAYOUT_DENSITY_OPTIONS):
        return "Adaptive"
    return value


def is_compact_layout() -> bool:
    return get_layout_density() == "Compact"


def get_grid_columns(default_columns: int) -> int:
    density = get_layout_density()
    if density == "Compact":
        return 1
    if density == "Comfort":
        return max(1, default_columns - 1)
    return max(1, default_columns)


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
        raise RuntimeError(
            "The API is taking too long to respond. Please try again."
        ) from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(
            "Could not reach the API. Make sure the backend is running on "
            "localhost:8000."
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
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="420"
        height="620"
        viewBox="0 0 420 620"
    >
        <defs>
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#143642"/>
                <stop offset="55%" stop-color="#12736b"/>
                <stop offset="100%" stop-color="#d6982f"/>
            </linearGradient>
        </defs>
        <rect width="420" height="620" rx="36" fill="url(#bg)"/>
        <rect
            x="36"
            y="36"
            width="348"
            height="548"
            rx="28"
            fill="rgba(255,255,255,0.12)"
        />
        <text
            x="210"
            y="240"
            text-anchor="middle"
            font-family="Georgia, serif"
            font-size="34"
            fill="#fff6ea"
        >
            Book Tracker
        </text>
        <text
            x="210"
            y="305"
            text-anchor="middle"
            font-family="Segoe UI, sans-serif"
            font-size="22"
            fill="#f7f1e7"
        >
            {short_title}
        </text>
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
    return f"Status: {label}"


def render_status_chip(status: str) -> None:
    label = get_status_label(status)
    status_class = STATUS_CHIP_CLASS.get(status, "bt-chip-want")
    st.markdown(
        f'<span class="bt-chip {status_class}">{escape(label)}</span>',
        unsafe_allow_html=True,
    )


def get_progress_value(book: dict[str, Any], field: str, default: Any = None) -> Any:
    progress = book.get("progress") or {}
    return progress.get(field, default)


def format_rating(value: int) -> str:
    if value <= 0:
        return "No rating"
    filled = chr(9733) * value
    empty = chr(9734) * (5 - value)
    return f"{filled}{empty}"


def _normalize_quick_isbn(raw_isbn: str) -> str | None:
    cleaned = raw_isbn.strip()
    if not cleaned:
        return None
    compact = "".join(char for char in cleaned if char not in {"-", " "}).upper()
    if len(compact) not in {10, 13}:
        raise ValueError("ISBN must be 10 or 13 characters.")
    if len(compact) == 10 and not (
        compact[:-1].isdigit() and (compact[-1].isdigit() or compact[-1] == "X")
    ):
        raise ValueError("ISBN-10 must contain 9 digits and a final digit or X.")
    if len(compact) == 13 and not compact.isdigit():
        raise ValueError("ISBN-13 must contain only digits.")
    return compact


def render_quick_book_panel(book: dict[str, Any], key_prefix: str) -> None:
    st.markdown(f"#### {escape(str(book.get('title') or 'Untitled'))}")
    st.caption(f"{book.get('author') or 'Unknown author'}")
    render_status_chip(get_book_status(book))
    st.markdown(
        '<p class="bt-panel-note">Quick edit without leaving this page.</p>',
        unsafe_allow_html=True,
    )

    default_total_pages = (
        "" if book.get("total_pages") is None else str(book.get("total_pages"))
    )

    with st.form(f"{key_prefix}_quick_edit_form", clear_on_submit=False):
        quick_title = st.text_input(
            "Title", value=str(book.get("title") or ""), key=f"{key_prefix}_quick_title"
        )
        quick_author = st.text_input(
            "Author",
            value=str(book.get("author") or ""),
            key=f"{key_prefix}_quick_author",
        )
        quick_isbn = st.text_input(
            "ISBN", value=str(book.get("isbn") or ""), key=f"{key_prefix}_quick_isbn"
        )
        quick_genre = st.text_input(
            "Genre", value=str(book.get("genre") or ""), key=f"{key_prefix}_quick_genre"
        )
        quick_total_pages = st.text_input(
            "Total Pages",
            value=default_total_pages,
            key=f"{key_prefix}_quick_total_pages",
        )
        quick_cover_url = st.text_input(
            "Cover URL",
            value=str(book.get("cover_url") or ""),
            key=f"{key_prefix}_quick_cover_url",
        )
        save_quick_edit = st.form_submit_button(
            "Save Quick Edit", width="stretch", type="primary"
        )

    if save_quick_edit:
        try:
            raw_total_pages = quick_total_pages.strip()
            total_pages = int(raw_total_pages) if raw_total_pages else None
            if total_pages is not None and total_pages < 0:
                raise ValueError("Total pages must be zero or greater.")

            payload = {
                "title": quick_title.strip(),
                "author": quick_author.strip(),
                "isbn": _normalize_quick_isbn(quick_isbn),
                "genre": quick_genre.strip() or None,
                "total_pages": total_pages,
                "cover_url": quick_cover_url.strip() or None,
            }
            if not payload["title"] or not payload["author"]:
                raise ValueError("Title and author are required.")

            api_request("PUT", f"/books/{book['id']}", json=payload)
            st.toast("Book updated.")
            st.rerun()
        except (RuntimeError, ValueError) as exc:
            st.error(str(exc))

    action_col_1, action_col_2 = st.columns(2)
    with action_col_1:
        if st.button("Full Edit", key=f"{key_prefix}_full_edit", width="stretch"):
            st.session_state["book_id"] = book["id"]
            st.session_state["editing_book_id"] = book["id"]
            st.session_state["book_form_loaded_id"] = None
            go_to_page(ADD_BOOK_PAGE)
    with action_col_2:
        if st.button(
            "Track", key=f"{key_prefix}_track", width="stretch", type="secondary"
        ):
            st.session_state["selected_book_id"] = book["id"]
            go_to_page(PROGRESS_PAGE)


def render_quick_book_panel_trigger(
    book: dict[str, Any], key_prefix: str, label: str = "Details"
) -> None:
    if hasattr(st, "popover"):
        with st.popover(label):
            render_quick_book_panel(book, key_prefix)
    else:
        with st.expander(label, expanded=False):
            render_quick_book_panel(book, key_prefix)


def build_book_options(books: list[dict[str, Any]]) -> list[tuple[str, int]]:
    return [(f"{book['title']} by {book['author']}", int(book["id"])) for book in books]
