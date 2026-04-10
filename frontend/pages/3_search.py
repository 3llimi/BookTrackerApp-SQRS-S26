from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from shared import (  # noqa: E402
    ADD_BOOK_PAGE,
    PROGRESS_PAGE,
    api_request,
    configure_page,
    format_rating,
    get_book_status,
    is_compact_layout,
    get_progress_value,
    get_status_badge,
    go_to_page,
    render_empty_state,
    render_hero,
    render_quick_book_panel_trigger,
    render_sidebar,
    render_status_chip,
    require_auth,
)

STATUS_FILTER_MAP = {
    "Want to Read": "not_started",
    "Reading": "reading",
    "Finished": "completed",
}

SORT_FIELD_MAP = {
    "Created Date": "created_at",
    "Title": "title",
    "Rating": "rating",
    "Pages Read": "pages_read",
}


configure_page("Search")
require_auth()
render_sidebar("pages/3_search.py")
render_hero(
    "Search Your Collection",
    (
        "Search by title or author, refine with focused filters, and jump "
        "directly to edit or progress tracking."
    ),
    kicker="Search & Filter",
)

compact_layout = is_compact_layout()

try:
    all_books = api_request(
        "GET",
        "/books/",
        params={"limit": 200, "sort": "title", "order": "asc"},
    )
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

genre_options = ["All"] + sorted(
    {book.get("genre") for book in all_books if book.get("genre")}
)
author_options = ["All"] + sorted(
    {book.get("author") for book in all_books if book.get("author")}
)
status_options = ["All", "Want to Read", "Reading", "Finished"]

defaults = {
    "search_genre_filter": "All",
    "search_author_filter": "All",
    "search_status_filter": "All",
    "search_sort_field": "Created Date",
    "search_sort_order": "Descending",
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)

if st.session_state.pop("search_clear_pending", False):
    st.session_state["search_query_input"] = ""
    st.session_state["search_genre_filter"] = "All"
    st.session_state["search_author_filter"] = "All"
    st.session_state["search_status_filter"] = "All"
    st.session_state["search_sort_field"] = "Created Date"
    st.session_state["search_sort_order"] = "Descending"

if st.session_state["search_genre_filter"] not in genre_options:
    st.session_state["search_genre_filter"] = "All"
if st.session_state["search_author_filter"] not in author_options:
    st.session_state["search_author_filter"] = "All"
if st.session_state["search_status_filter"] not in status_options:
    st.session_state["search_status_filter"] = "All"
if st.session_state["search_sort_field"] not in SORT_FIELD_MAP:
    st.session_state["search_sort_field"] = "Created Date"
if st.session_state["search_sort_order"] not in ["Descending", "Ascending"]:
    st.session_state["search_sort_order"] = "Descending"

with st.sidebar:
    st.markdown("### Filters")
    st.selectbox("Genre", genre_options, key="search_genre_filter")
    st.selectbox("Author", author_options, key="search_author_filter")
    st.selectbox("Status", status_options, key="search_status_filter")
    st.selectbox("Sort Field", list(SORT_FIELD_MAP.keys()), key="search_sort_field")
    st.selectbox("Sort Order", ["Descending", "Ascending"], key="search_sort_order")
    if st.button("Clear Filters", width="stretch", type="secondary"):
        st.session_state["search_clear_pending"] = True
        st.rerun()

query = st.text_input(
    "Search Books",
    key="search_query_input",
    placeholder="Start typing a title or author...",
)

selected_genre = st.session_state["search_genre_filter"]
selected_author = st.session_state["search_author_filter"]
selected_status = st.session_state["search_status_filter"]
selected_sort_field = st.session_state["search_sort_field"]
selected_sort_order = st.session_state["search_sort_order"]

params = {
    "limit": 200,
    "sort": (
        "created_at"
        if selected_sort_field == "Pages Read"
        else SORT_FIELD_MAP[selected_sort_field]
    ),
    "order": "asc" if selected_sort_order == "Ascending" else "desc",
}

if query.strip():
    params["title"] = query.strip()
if selected_genre != "All":
    params["genre"] = selected_genre
if selected_author != "All":
    params["author"] = selected_author
if selected_status != "All":
    params["status"] = STATUS_FILTER_MAP[selected_status]

try:
    with st.spinner("Searching your collection..."):
        results = api_request("GET", "/books/", params=params)
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

reverse_sort = selected_sort_order == "Descending"


def _search_sort_key(book: dict[str, object]):
    if selected_sort_field == "Rating":
        return int(get_progress_value(book, "rating", 0) or 0)
    if selected_sort_field == "Pages Read":
        return int(get_progress_value(book, "current_page", 0) or 0)
    if selected_sort_field == "Title":
        return str(book.get("title") or "").lower()
    value = book.get("created_at")
    return str(value or "")


results = sorted(results, key=_search_sort_key, reverse=reverse_sort)

result_count = len(results)
st.caption(f"{result_count} result{'s' if result_count != 1 else ''}")

if compact_layout:
    summary_col_1, summary_col_2 = st.columns(2)
    summary_col_1.metric("Results", result_count)
    summary_col_2.metric(
        "Reading", sum(1 for book in results if get_book_status(book) == "reading")
    )
    st.metric(
        "Rated",
        sum(1 for book in results if get_progress_value(book, "rating") is not None),
    )
else:
    summary_col_1, summary_col_2, summary_col_3 = st.columns(3)
    summary_col_1.metric("Results", result_count)
    summary_col_2.metric(
        "Reading", sum(1 for book in results if get_book_status(book) == "reading")
    )
    summary_col_3.metric(
        "Rated",
        sum(1 for book in results if get_progress_value(book, "rating") is not None),
    )

if not results:
    render_empty_state(
        "No books match your filters",
        "Try a broader search term or clear one of the sidebar filters.",
    )
    st.stop()

for book in results:
    status = get_book_status(book)
    current_page = int(get_progress_value(book, "current_page", 0) or 0)
    total_pages = int(book.get("total_pages") or 0)
    rating = int(get_progress_value(book, "rating") or 0)
    with st.container(border=True):
        if compact_layout:
            st.markdown(f"**{book['title']}**")
            st.caption(
                (
                    f"{book['author']} | {book.get('genre') or 'No Genre'} | "
                    f"{format_rating(rating)}"
                )
            )
            if total_pages > 0:
                st.progress(min(current_page / total_pages, 1.0))
                st.caption(f"{current_page} / {total_pages} pages")
            else:
                st.caption("No total pages set")

            action_col_1, action_col_2, action_col_3 = st.columns(3)
            with action_col_1:
                render_status_chip(status)
                st.caption(get_status_badge(status))
            with action_col_2:
                if st.button(
                    "Track",
                    key=f"search_track_{book['id']}",
                    width="stretch",
                    type="primary",
                ):
                    st.session_state["selected_book_id"] = book["id"]
                    go_to_page(PROGRESS_PAGE)
            with action_col_3:
                render_quick_book_panel_trigger(
                    book, key_prefix=f"search_{book['id']}", label="Details"
                )
        else:
            content_col, action_col = st.columns([4.0, 1.5])
            with content_col:
                st.markdown(f"**{book['title']}**")
                st.caption(
                    (
                        f"{book['author']} | {book.get('genre') or 'No Genre'} | "
                        f"{format_rating(rating)}"
                    )
                )
                if total_pages > 0:
                    st.progress(min(current_page / total_pages, 1.0))
                    st.caption(f"{current_page} / {total_pages} pages")
                else:
                    st.caption("No total pages set")
            with action_col:
                render_status_chip(status)
                st.caption(get_status_badge(status))
                if st.button(
                    "Track",
                    key=f"search_track_{book['id']}",
                    width="stretch",
                    type="primary",
                ):
                    st.session_state["selected_book_id"] = book["id"]
                    go_to_page(PROGRESS_PAGE)
                if st.button(
                    "Edit",
                    key=f"search_edit_{book['id']}",
                    width="stretch",
                    type="secondary",
                ):
                    st.session_state["book_id"] = book["id"]
                    st.session_state["editing_book_id"] = book["id"]
                    st.session_state["book_form_loaded_id"] = None
                    go_to_page(ADD_BOOK_PAGE)
                render_quick_book_panel_trigger(
                    book, key_prefix=f"search_{book['id']}", label="Details"
                )
