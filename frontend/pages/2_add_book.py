from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st

from shared import (
    MY_BOOKS_PAGE,
    api_request,
    configure_page,
    cover_image_source,
    go_to_page,
    render_hero,
    render_sidebar,
    require_auth,
)

FORM_FIELDS = {
    "title": "book_form_title",
    "author": "book_form_author",
    "isbn": "book_form_isbn",
    "genre": "book_form_genre",
    "total_pages": "book_form_total_pages",
    "cover_url": "book_form_cover_url",
}


def set_form_values(book_data: dict[str, object]) -> None:
    st.session_state[FORM_FIELDS["title"]] = book_data.get("title", "") or ""
    st.session_state[FORM_FIELDS["author"]] = book_data.get("author", "") or ""
    st.session_state[FORM_FIELDS["isbn"]] = book_data.get("isbn", "") or ""
    st.session_state[FORM_FIELDS["genre"]] = book_data.get("genre", "") or ""
    total_pages = book_data.get("total_pages")
    st.session_state[FORM_FIELDS["total_pages"]] = "" if total_pages is None else str(total_pages)
    st.session_state[FORM_FIELDS["cover_url"]] = book_data.get("cover_url", "") or ""


def reset_form() -> None:
    set_form_values({})
    st.session_state["book_id"] = None
    st.session_state["editing_book_id"] = None
    st.session_state["book_form_loaded_id"] = None


def get_form_payload() -> dict[str, object]:
    raw_total_pages = str(st.session_state.get(FORM_FIELDS["total_pages"], "") or "").strip()
    total_pages: int | None = None
    if raw_total_pages:
        total_pages = int(raw_total_pages)
    return {
        "title": st.session_state.get(FORM_FIELDS["title"], "").strip(),
        "author": st.session_state.get(FORM_FIELDS["author"], "").strip(),
        "isbn": st.session_state.get(FORM_FIELDS["isbn"], "").strip() or None,
        "genre": st.session_state.get(FORM_FIELDS["genre"], "").strip() or None,
        "total_pages": total_pages,
        "cover_url": st.session_state.get(FORM_FIELDS["cover_url"], "").strip() or None,
    }


def show_openlibrary_timeout(message: str) -> bool:
    lowered = message.lower()
    return "timed out" in lowered or "taking too long" in lowered


configure_page("Add Book")
require_auth()
render_sidebar("pages/2_add_book.py")

editing_book_id = st.session_state.get("book_id") or st.session_state.get("editing_book_id")
st.session_state["book_id"] = editing_book_id
st.session_state["editing_book_id"] = editing_book_id
is_edit_mode = editing_book_id is not None

if editing_book_id and st.session_state.get("book_form_loaded_id") != editing_book_id:
    try:
        with st.spinner("Loading book details..."):
            book_details = api_request("GET", f"/books/{editing_book_id}")
        set_form_values(book_details)
        st.session_state["book_form_loaded_id"] = editing_book_id
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

render_hero(
    "Edit Book" if is_edit_mode else "Add Book",
    "Keep the form simple, import details from Open Library when it helps, and save everything with one clear submit action.",
    kicker="Book Form",
)

action_col, back_col = st.columns([1, 1])
with action_col:
    if st.button("Start a fresh form", width="stretch", type="secondary"):
        reset_form()
        st.toast("Ready for a new book.")
        st.rerun()
with back_col:
    if st.button("Back to My Books", width="stretch"):
        go_to_page(MY_BOOKS_PAGE)

with st.expander("Import from Open Library", expanded=False):
    openlibrary_query = st.text_input(
        "Search by title, author, or ISBN",
        key="openlibrary_query",
        placeholder="The Name of the Wind",
    )

    query_clean = openlibrary_query.strip()
    if not query_clean:
        st.session_state["openlibrary_results"] = []
        st.session_state["openlibrary_last_query"] = ""
    elif query_clean != st.session_state.get("openlibrary_last_query", ""):
        st.session_state["openlibrary_last_query"] = query_clean
        try:
            with st.spinner("Searching Open Library..."):
                st.session_state["openlibrary_results"] = api_request(
                    "GET",
                    "/openlibrary/search",
                    params={"q": query_clean},
                )[:5]
        except RuntimeError as exc:
            st.session_state["openlibrary_results"] = []
            if show_openlibrary_timeout(str(exc)):
                st.info("Open Library is taking a little longer than usual. Please try again in a moment.")
            else:
                st.error(str(exc))

    results = st.session_state.get("openlibrary_results", [])
    if results:
        for idx, result in enumerate(results):
            isbn = result.get("isbn")
            with st.container(border=True):
                card_col, body_col, action_col = st.columns([1.1, 2.4, 1.1])
                with card_col:
                    st.image(
                        cover_image_source(result.get("title", "Book"), result.get("cover_url")),
                        width="stretch",
                    )
                with body_col:
                    st.markdown(f"**{result.get('title') or 'Untitled'}**")
                    st.caption(
                        f"{result.get('author') or 'Unknown author'}"
                        + (
                            f" | {result.get('first_publish_year')}"
                            if result.get("first_publish_year")
                            else ""
                        )
                    )
                    if isbn:
                        st.caption(f"ISBN: {isbn}")
                    else:
                        st.caption("No ISBN available for this result.")
                with action_col:
                    unique_suffix = isbn or f"{result.get('title','book')}_{idx}"
                    if st.button(
                        "Use this book",
                        key=f"openlibrary_import_{unique_suffix}",
                        width="stretch",
                    ):
                        try:
                            if isbn:
                                with st.spinner("Importing book details..."):
                                    detail = api_request("GET", f"/openlibrary/book/{isbn}")
                            else:
                                detail = {
                                    "title": result.get("title") or "",
                                    "author": result.get("author") or "",
                                    "isbn": None,
                                    "cover_url": result.get("cover_url"),
                                    "total_pages": None,
                                    "genre": "",
                                }
                            detail["author"] = detail.get("author") or result.get("author") or ""
                            detail["genre"] = detail.get("genre") or st.session_state.get(FORM_FIELDS["genre"], "")
                            set_form_values(detail)
                            st.toast("Book details imported into the form.")
                            st.rerun()
                        except RuntimeError as exc:
                            if show_openlibrary_timeout(str(exc)):
                                st.info("Open Library timed out while importing. Please try again.")
                            else:
                                st.error(str(exc))

preview_cover = st.session_state.get(FORM_FIELDS["cover_url"], "")
preview_title = st.session_state.get(FORM_FIELDS["title"], "Book cover")
preview_col, form_col = st.columns([1.1, 1.9])

with preview_col:
    st.image(cover_image_source(preview_title, preview_cover), width="stretch")

with form_col:
    with st.form("book_form", clear_on_submit=False):
        st.text_input("Title", key=FORM_FIELDS["title"], placeholder="Atomic Habits")
        st.text_input("Author", key=FORM_FIELDS["author"], placeholder="James Clear")
        field_col_1, field_col_2 = st.columns(2)
        with field_col_1:
            st.text_input("ISBN", key=FORM_FIELDS["isbn"], placeholder="9780735211292")
            st.text_input(
                "Total pages",
                key=FORM_FIELDS["total_pages"],
                placeholder="320",
            )
        with field_col_2:
            st.text_input("Genre", key=FORM_FIELDS["genre"], placeholder="Self-help")
            st.text_input("Cover URL", key=FORM_FIELDS["cover_url"], placeholder="https://...")

        submit_label = "Save Changes" if is_edit_mode else "Add Book"
        submitted = st.form_submit_button(submit_label, width="stretch")

    if submitted:
        try:
            payload = get_form_payload()
        except ValueError:
            st.error("Total pages must be a valid whole number.")
            st.stop()

        if not payload["title"] or not payload["author"]:
            st.error("Title and author are required.")
        else:
            try:
                with st.spinner("Saving book..."):
                    if is_edit_mode:
                        saved_book = api_request("PUT", f"/books/{editing_book_id}", json=payload)
                    else:
                        saved_book = api_request("POST", "/books/", json=payload)
                st.session_state["book_id"] = saved_book["id"]
                st.session_state["editing_book_id"] = saved_book["id"]
                st.session_state["book_form_loaded_id"] = saved_book["id"]
                st.toast("Book saved successfully.")
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))
