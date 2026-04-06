from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st

from shared import (
    ADD_BOOK_PAGE,
    PROGRESS_PAGE,
    api_request,
    configure_page,
    cover_image_source,
    get_book_status,
    get_progress_value,
    get_status_badge,
    go_to_page,
    render_empty_state,
    render_hero,
    render_sidebar,
    require_auth,
)


configure_page("My Books")
require_auth()
render_sidebar("pages/1_my_books.py")
render_hero(
    "My Books",
    "Browse your collection, jump into editing, and keep progress updates one click away.",
    kicker="Your Library",
)

header_left, header_right = st.columns([3, 1])
with header_right:
    if st.button("Add a new book", width="stretch"):
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
        "Your shelf is still empty",
        "Add your first book to start tracking progress, ratings, and notes.",
    )
    st.stop()

st.write(f"**{len(books)} books in your collection**")

for row_start in range(0, len(books), 3):
    columns = st.columns(3)
    row_books = books[row_start : row_start + 3]

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
                st.markdown(f'<div class="bt-card-title">{book["title"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="bt-card-meta">{book["author"]}</div>', unsafe_allow_html=True)
                st.markdown(get_status_badge(status), unsafe_allow_html=True)

                if total_pages:
                    st.progress(min(current_page / total_pages, 1.0))
                    st.caption(f"{current_page} / {total_pages} pages")
                elif progress_pct is not None:
                    st.progress(min(progress_pct / 100, 1.0))
                    st.caption(f"{progress_pct}% completed")
                else:
                    st.caption("No reading progress yet")

                edit_col, progress_col, delete_col = st.columns(3)

                with edit_col:
                    if st.button("Edit", key=f"edit_{book['id']}", width="stretch"):
                        st.session_state["book_id"] = book["id"]
                        st.session_state["editing_book_id"] = book["id"]
                        st.session_state["book_form_loaded_id"] = None
                        go_to_page(ADD_BOOK_PAGE)

                with progress_col:
                    if st.button("Track", key=f"progress_{book['id']}", width="stretch"):
                        st.session_state["selected_book_id"] = book["id"]
                        go_to_page(PROGRESS_PAGE)

                with delete_col:
                    if st.button("Delete", key=f"delete_{book['id']}", width="stretch", type="secondary"):
                        try:
                            api_request("DELETE", f"/books/{book['id']}", expect_json=False)
                            if st.session_state.get("book_id") == book["id"]:
                                st.session_state["book_id"] = None
                            if st.session_state.get("editing_book_id") == book["id"]:
                                st.session_state["editing_book_id"] = None
                            if st.session_state.get("selected_book_id") == book["id"]:
                                st.session_state["selected_book_id"] = None
                            st.toast(f"Deleted '{book['title']}'.")
                            st.rerun()
                        except RuntimeError as exc:
                            st.error(str(exc))
