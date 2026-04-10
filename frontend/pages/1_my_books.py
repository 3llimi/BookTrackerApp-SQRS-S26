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
    cover_image_source,
    format_rating,
    get_book_status,
    get_grid_columns,
    is_compact_layout,
    get_progress_value,
    go_to_page,
    render_empty_state,
    render_hero,
    render_quick_book_panel_trigger,
    render_sidebar,
    render_status_chip,
    require_auth,
)

STATUS_FILTER_TO_API = {
    "All": None,
    "Want to Read": "not_started",
    "Reading": "reading",
    "Finished": "completed",
}

BOOK_SORT_OPTIONS = {
    "Rating (High to Low)": "rating",
    "Pages Read (High to Low)": "pages_read",
}


configure_page("My Books")
require_auth()
render_sidebar("pages/1_my_books.py")
render_hero(
    "My Books",
    (
        "Browse your collection, update details quickly, and keep your reading "
        "progress moving."
    ),
    kicker="Your Library",
)

compact_layout = is_compact_layout()
cards_per_row = get_grid_columns(3)

if compact_layout:
    st.markdown("#### Your Shelf")
    if st.button("Add New Book", width="stretch"):
        st.session_state["book_id"] = None
        st.session_state["editing_book_id"] = None
        st.session_state["book_form_loaded_id"] = None
        go_to_page(ADD_BOOK_PAGE)
else:
    header_left, header_right = st.columns([2.2, 1])
    with header_left:
        st.markdown("#### Your Shelf")
    with header_right:
        if st.button("Add New Book", width="stretch"):
            st.session_state["book_id"] = None
            st.session_state["editing_book_id"] = None
            st.session_state["book_form_loaded_id"] = None
            go_to_page(ADD_BOOK_PAGE)

try:
    with st.spinner("Loading your bookshelf..."):
        books = api_request(
            "GET",
            "/books/",
            params={"limit": 200, "sort": "created_at", "order": "desc"},
        )
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if not books:
    render_empty_state(
        "Your Shelf Is Empty",
        "Add your first book to start tracking progress, ratings, and notes.",
    )
    st.stop()

book_count = len(books)
st.caption(f"{book_count} book{'s' if book_count != 1 else ''} in your collection")

stats_total = len(books)
stats_reading = sum(1 for book in books if get_book_status(book) == "reading")
stats_finished = sum(1 for book in books if get_book_status(book) == "completed")
ratings = [
    int(get_progress_value(book, "rating") or 0)
    for book in books
    if get_progress_value(book, "rating") is not None
]
average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

if compact_layout:
    stat_col_1, stat_col_2 = st.columns(2)
    stat_col_3, stat_col_4 = st.columns(2)
    stat_col_1.metric("Total Books", stats_total)
    stat_col_2.metric("Currently Reading", stats_reading)
    stat_col_3.metric("Finished", stats_finished)
    stat_col_4.metric("Average Rating", average_rating if ratings else "N/A")
else:
    stat_col_1, stat_col_2, stat_col_3, stat_col_4 = st.columns(4)
    stat_col_1.metric("Total Books", stats_total)
    stat_col_2.metric("Currently Reading", stats_reading)
    stat_col_3.metric("Finished", stats_finished)
    stat_col_4.metric("Average Rating", average_rating if ratings else "N/A")

if compact_layout:
    query = st.text_input(
        "Find a Book",
        key="my_books_query",
        placeholder="Search by title or author...",
    ).strip()
    if st.session_state.get("my_books_sort") not in BOOK_SORT_OPTIONS:
        st.session_state["my_books_sort"] = "Rating (High to Low)"
    filter_col_1, filter_col_2 = st.columns(2)
    with filter_col_1:
        selected_status_label = st.selectbox(
            "Status",
            list(STATUS_FILTER_TO_API.keys()),
            key="my_books_status_filter",
        )
    with filter_col_2:
        selected_sort_label = st.selectbox(
            "Sort",
            list(BOOK_SORT_OPTIONS.keys()),
            key="my_books_sort",
        )
    if st.button(
        "Clear", key="my_books_clear_filters", width="stretch", type="secondary"
    ):
        st.session_state["my_books_query"] = ""
        st.session_state["my_books_status_filter"] = "All"
        st.session_state["my_books_sort"] = "Rating (High to Low)"
        st.rerun()
else:
    if st.session_state.get("my_books_sort") not in BOOK_SORT_OPTIONS:
        st.session_state["my_books_sort"] = "Rating (High to Low)"
    filter_col_1, filter_col_2, filter_col_3, filter_col_4 = st.columns(
        [2.0, 1.0, 1.2, 0.8]
    )
    with filter_col_1:
        query = st.text_input(
            "Find a Book",
            key="my_books_query",
            placeholder="Search by title or author...",
        ).strip()
    with filter_col_2:
        selected_status_label = st.selectbox(
            "Status",
            list(STATUS_FILTER_TO_API.keys()),
            key="my_books_status_filter",
        )
    with filter_col_3:
        selected_sort_label = st.selectbox(
            "Sort",
            list(BOOK_SORT_OPTIONS.keys()),
            key="my_books_sort",
        )
    with filter_col_4:
        st.write("")
        if st.button(
            "Clear", key="my_books_clear_filters", width="stretch", type="secondary"
        ):
            st.session_state["my_books_query"] = ""
            st.session_state["my_books_status_filter"] = "All"
            st.session_state["my_books_sort"] = "Rating (High to Low)"
            st.rerun()

status_filter = STATUS_FILTER_TO_API[selected_status_label]
query_lower = query.lower()

filtered_books = []
for book in books:
    if status_filter and get_book_status(book) != status_filter:
        continue
    if query:
        title = str(book.get("title") or "").lower()
        author = str(book.get("author") or "").lower()
        if query_lower not in title and query_lower not in author:
            continue
    filtered_books.append(book)

selected_sort_mode = BOOK_SORT_OPTIONS[selected_sort_label]


def _book_sort_key(book: dict[str, object]):
    if selected_sort_mode == "rating":
        return int(get_progress_value(book, "rating") or 0)
    return int(get_progress_value(book, "current_page", 0) or 0)


filtered_books.sort(key=_book_sort_key, reverse=True)

if not filtered_books:
    render_empty_state(
        "No Books Match These Filters",
        "Try a broader search term or clear filters to see your full collection.",
    )
    st.stop()

pending_delete_book_id = st.session_state.get("pending_delete_book_id")

for row_start in range(0, len(filtered_books), cards_per_row):
    columns = st.columns(cards_per_row, gap="large")
    row_books = filtered_books[row_start : row_start + cards_per_row]

    for column, book in zip(columns, row_books):
        with column:
            status = get_book_status(book)
            progress_pct = book.get("progress_percentage")
            current_page = get_progress_value(book, "current_page", 0) or 0
            total_pages = book.get("total_pages") or 0

            with st.container(border=True):
                st.image(
                    cover_image_source(book["title"], book.get("cover_url")),
                    width="stretch",
                )
                st.subheader(book["title"])
                st.caption(book["author"])
                genre = book.get("genre") or "No Genre"
                st.caption(
                    (
                        f"{genre} | "
                        f"{format_rating(int(get_progress_value(book, 'rating') or 0))}"
                    )
                )
                render_status_chip(status)

                if total_pages:
                    st.progress(min(current_page / total_pages, 1.0))
                    st.caption(f"{current_page} / {total_pages} pages")
                elif progress_pct is not None:
                    st.progress(min(progress_pct / 100, 1.0))
                    st.caption(f"{progress_pct}% completed")
                else:
                    st.caption("No reading progress yet")

                top_action_col_1, top_action_col_2 = st.columns(2)
                with top_action_col_1:
                    if st.button("Edit", key=f"edit_{book['id']}", width="stretch"):
                        st.session_state["book_id"] = book["id"]
                        st.session_state["editing_book_id"] = book["id"]
                        st.session_state["book_form_loaded_id"] = None
                        go_to_page(ADD_BOOK_PAGE)
                with top_action_col_2:
                    if st.button(
                        "Progress", key=f"progress_{book['id']}", width="stretch"
                    ):
                        st.session_state["selected_book_id"] = book["id"]
                        go_to_page(PROGRESS_PAGE)

                bottom_action_col_1, bottom_action_col_2 = st.columns(2)
                with bottom_action_col_1:
                    render_quick_book_panel_trigger(
                        book, key_prefix=f"my_books_{book['id']}", label="Details"
                    )
                delete_column = bottom_action_col_2

                with delete_column:
                    if pending_delete_book_id == book["id"]:
                        st.warning("Delete this book?")
                        confirm_col, cancel_col = st.columns(2)
                        with confirm_col:
                            if st.button(
                                "Confirm",
                                key=f"confirm_delete_{book['id']}",
                                width="stretch",
                            ):
                                try:
                                    api_request(
                                        "DELETE",
                                        f"/books/{book['id']}",
                                        expect_json=False,
                                    )
                                    if st.session_state.get("book_id") == book["id"]:
                                        st.session_state["book_id"] = None
                                    if (
                                        st.session_state.get("editing_book_id")
                                        == book["id"]
                                    ):
                                        st.session_state["editing_book_id"] = None
                                    if (
                                        st.session_state.get("selected_book_id")
                                        == book["id"]
                                    ):
                                        st.session_state["selected_book_id"] = None
                                    st.session_state["pending_delete_book_id"] = None
                                    st.toast(f"Deleted '{book['title']}'.")
                                    st.rerun()
                                except RuntimeError as exc:
                                    st.error(str(exc))
                        with cancel_col:
                            if st.button(
                                "Cancel",
                                key=f"cancel_delete_{book['id']}",
                                width="stretch",
                                type="secondary",
                            ):
                                st.session_state["pending_delete_book_id"] = None
                                st.rerun()
                    elif st.button(
                        "Delete",
                        key=f"delete_{book['id']}",
                        width="stretch",
                        type="secondary",
                    ):
                        st.session_state["pending_delete_book_id"] = book["id"]
                        st.rerun()
