from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import time

import streamlit as st

from shared import (
    PROGRESS_PAGE,
    api_request,
    configure_page,
    get_book_status,
    get_status_text,
    go_to_page,
    render_empty_state,
    render_hero,
    render_sidebar,
    require_auth,
    show_notice,
)

STATUS_FILTER_MAP = {
    "Want to Read": "not_started",
    "Reading": "reading",
    "Finished": "completed",
}

SORT_FIELD_MAP = {
    "Created date": "created_at",
    "Title": "title",
    "Author": "author",
    "Rating": "rating",
}


configure_page("Search")
require_auth()
render_sidebar("pages/3_search.py")
render_hero(
    "Search Your Collection",
    "Type to search across your library. Filters and sorting are applied instantly while you type.",
    kicker="Search & Filter",
)
show_notice()

try:
    all_books = api_request(
        "GET",
        "/books/",
        params={"limit": 200, "sort": "title", "order": "asc"},
    )
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

with st.sidebar:
    st.markdown("### Filters")
    genre_options = ["All"] + sorted({book.get("genre") for book in all_books if book.get("genre")})
    author_options = ["All"] + sorted({book.get("author") for book in all_books if book.get("author")})
    status_options = ["All", "Want to Read", "Reading", "Finished"]

    selected_genre = st.selectbox("Genre", genre_options, index=0)
    selected_author = st.selectbox("Author", author_options, index=0)
    selected_status = st.selectbox("Status", status_options, index=0)
    selected_sort_field = st.selectbox("Sort field", list(SORT_FIELD_MAP.keys()), index=0)
    selected_sort_order = st.selectbox("Sort order", ["Descending", "Ascending"], index=0)

query = st.text_input(
    "Search books",
    key="search_query_input",
    placeholder="Start typing a title or author...",
)

if query != st.session_state.get("search_last_value", ""):
    st.session_state["search_last_value"] = query
    time.sleep(0.3)

params = {
    "limit": 200,
    "sort": SORT_FIELD_MAP[selected_sort_field],
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

st.write(f"**{len(results)} result(s)**")
st.caption("Click a row to open that book in the Progress page.")

if not results:
    render_empty_state(
        "No books match your filters",
        "Try a broader search term or clear one of the sidebar filters.",
    )
    st.stop()

for book in results:
    status = get_book_status(book)
    with st.container(border=True):
        row_label = f'{book["title"]} | {book["author"]} | {book.get("genre") or "No genre"}'
        if st.button(row_label, key=f"search_row_{book['id']}", width="stretch", type="secondary"):
            st.session_state["selected_book_id"] = book["id"]
            go_to_page(PROGRESS_PAGE)
        st.caption(f"Status: {get_status_text(status)}")
