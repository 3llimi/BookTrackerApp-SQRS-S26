from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from shared import (  # noqa: E402
    MY_BOOKS_PAGE,
    api_request,
    configure_page,
    cover_image_source,
    go_to_page,
    is_compact_layout,
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
    st.session_state[FORM_FIELDS["total_pages"]] = (
        "" if total_pages is None else str(total_pages)
    )
    st.session_state[FORM_FIELDS["cover_url"]] = book_data.get("cover_url", "") or ""


def reset_form() -> None:
    set_form_values({})
    st.session_state["book_id"] = None
    st.session_state["editing_book_id"] = None
    st.session_state["book_form_loaded_id"] = None


def handle_post_save(saved_book_id: int, editing: bool) -> None:
    wants_another = bool(st.session_state.get("book_form_add_another", False))

    if editing or not wants_another:
        st.session_state["book_id"] = saved_book_id
        st.session_state["editing_book_id"] = saved_book_id
        st.session_state["book_form_loaded_id"] = saved_book_id
        st.toast("Book saved successfully.")
        go_to_page(MY_BOOKS_PAGE)

    st.session_state["book_form_reset_pending"] = True
    st.session_state["book_form_notice"] = "Book saved. Add another one."
    st.rerun()


def merge_openlibrary_import_data(
    result: dict[str, object],
    detail: dict[str, object],
    fallback_isbn: str | None,
) -> dict[str, object]:
    total_pages = detail.get("total_pages")
    if total_pages is None:
        total_pages = result.get("total_pages")

    merged = {
        "title": (detail.get("title") or result.get("title") or "").strip(),
        "author": (detail.get("author") or result.get("author") or "").strip(),
        "isbn": (
            detail.get("isbn") or fallback_isbn or result.get("isbn") or ""
        ).strip()
        or None,
        "cover_url": (detail.get("cover_url") or result.get("cover_url") or "").strip()
        or None,
        "total_pages": total_pages,
        "genre": (detail.get("genre") or result.get("genre") or "").strip() or None,
    }

    return merged


def get_form_payload() -> dict[str, object]:
    raw_total_pages = str(
        st.session_state.get(FORM_FIELDS["total_pages"], "") or ""
    ).strip()
    total_pages: int | None = None
    if raw_total_pages:
        total_pages = int(raw_total_pages)
    if total_pages is not None and total_pages < 0:
        raise ValueError("Total pages must be zero or greater.")

    raw_isbn = str(st.session_state.get(FORM_FIELDS["isbn"], "") or "").strip()
    isbn = normalize_isbn(raw_isbn)

    return {
        "title": st.session_state.get(FORM_FIELDS["title"], "").strip(),
        "author": st.session_state.get(FORM_FIELDS["author"], "").strip(),
        "isbn": isbn,
        "genre": st.session_state.get(FORM_FIELDS["genre"], "").strip() or None,
        "total_pages": total_pages,
        "cover_url": st.session_state.get(FORM_FIELDS["cover_url"], "").strip() or None,
    }


def normalize_isbn(raw_isbn: str) -> str | None:
    if not raw_isbn:
        return None

    compact = "".join(char for char in raw_isbn if char not in {"-", " "}).upper()
    if len(compact) not in {10, 13}:
        raise ValueError(
            "ISBN must be 10 or 13 characters (excluding spaces and hyphens)."
        )
    if len(compact) == 10 and not (
        compact[:-1].isdigit() and (compact[-1].isdigit() or compact[-1] == "X")
    ):
        raise ValueError("ISBN-10 must contain 9 digits and a final digit or X.")
    if len(compact) == 13 and not compact.isdigit():
        raise ValueError("ISBN-13 must contain only digits.")
    return compact


def normalize_isbn_query(raw_query: str) -> str | None:
    candidate = raw_query.strip()
    if not candidate:
        return None
    try:
        return normalize_isbn(candidate)
    except ValueError:
        return None


def show_openlibrary_timeout(message: str) -> bool:
    lowered = message.lower()
    return "timed out" in lowered or "taking too long" in lowered


configure_page("Add Book")
require_auth()
render_sidebar("pages/2_add_book.py")

if st.session_state.pop("book_form_reset_pending", False):
    reset_form()
    st.session_state["book_form_add_another"] = False
    st.session_state["openlibrary_expanded"] = False
    st.session_state["openlibrary_results"] = []
    st.session_state["openlibrary_last_query"] = ""
    st.session_state["openlibrary_query"] = ""
    st.session_state["openlibrary_clear_query_pending"] = False

book_form_notice = st.session_state.pop("book_form_notice", None)
if book_form_notice:
    st.success(book_form_notice)

editing_book_id = st.session_state.get("book_id") or st.session_state.get(
    "editing_book_id"
)
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
    (
        "Keep the form simple, import details from Open Library when useful, "
        "and save with one clear action."
    ),
    kicker="Book Form",
)

compact_layout = is_compact_layout()
st.session_state.setdefault("book_form_add_another", False)

st.caption("Tip: Import first, then fine-tune the details before saving.")

if compact_layout:
    if st.button("Start a Fresh Form", width="stretch", type="secondary"):
        reset_form()
        st.session_state["openlibrary_expanded"] = False
        st.toast("Ready for a new book.")
        st.rerun()
    if st.button("Back to My Books", width="stretch"):
        go_to_page(MY_BOOKS_PAGE)
else:
    action_col, back_col = st.columns([1, 1])
    with action_col:
        if st.button("Start a Fresh Form", width="stretch", type="secondary"):
            reset_form()
            st.session_state["openlibrary_expanded"] = False
            st.toast("Ready for a new book.")
            st.rerun()
    with back_col:
        if st.button("Back to My Books", width="stretch"):
            go_to_page(MY_BOOKS_PAGE)

with st.expander(
    "Import from Open Library",
    expanded=st.session_state.get("openlibrary_expanded", False),
):
    if st.session_state.get("openlibrary_clear_query_pending"):
        st.session_state["openlibrary_query"] = ""
        st.session_state["openlibrary_clear_query_pending"] = False

    openlibrary_query = st.text_input(
        "Search by Title, Author, or ISBN",
        key="openlibrary_query",
        placeholder="The Name of the Wind",
    )

    query_clean = openlibrary_query.strip()
    if not query_clean:
        st.session_state["openlibrary_results"] = []
        st.session_state["openlibrary_last_query"] = ""
        st.session_state["openlibrary_expanded"] = False
    elif query_clean != st.session_state.get("openlibrary_last_query", ""):
        st.session_state["openlibrary_expanded"] = True
        st.session_state["openlibrary_last_query"] = query_clean
        isbn_query = normalize_isbn_query(query_clean)
        try:
            if isbn_query:
                with st.spinner("Looking up ISBN in Open Library..."):
                    detail = api_request("GET", f"/openlibrary/book/{isbn_query}")

                if detail.get("title"):
                    st.session_state["openlibrary_results"] = [
                        {
                            "title": detail.get("title"),
                            "author": detail.get("author"),
                            "isbn": detail.get("isbn") or isbn_query,
                            "cover_url": detail.get("cover_url"),
                            "first_publish_year": None,
                            "genre": detail.get("genre"),
                            "total_pages": detail.get("total_pages"),
                        }
                    ]
                else:
                    st.session_state["openlibrary_results"] = []
            else:
                with st.spinner("Searching Open Library..."):
                    st.session_state["openlibrary_results"] = api_request(
                        "GET",
                        "/openlibrary/search",
                        params={"q": query_clean},
                    )[:5]
        except RuntimeError as exc:
            st.session_state["openlibrary_results"] = []
            if show_openlibrary_timeout(str(exc)):
                st.info(
                    (
                        "Open Library is taking a little longer than usual. "
                        "Please try again in a moment."
                    )
                )
            else:
                st.error(str(exc))

    results = st.session_state.get("openlibrary_results", [])
    if results:
        for idx, result in enumerate(results):
            isbn = result.get("isbn")
            genre_from_search = (result.get("genre") or "").strip()
            with st.container(border=True):
                if compact_layout:
                    st.image(
                        cover_image_source(
                            result.get("title", "Book"), result.get("cover_url")
                        ),
                        width="stretch",
                    )
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
                    if genre_from_search:
                        st.caption(f"Genre: {genre_from_search}")
                    unique_suffix = isbn or f"{result.get('title', 'book')}_{idx}"
                    if st.button(
                        "Use This Book",
                        key=f"openlibrary_import_{unique_suffix}",
                        width="stretch",
                    ):
                        try:
                            if isbn:
                                with st.spinner("Importing book details..."):
                                    detail = api_request(
                                        "GET", f"/openlibrary/book/{isbn}"
                                    )
                            else:
                                detail = {
                                    "title": result.get("title") or "",
                                    "author": result.get("author") or "",
                                    "isbn": None,
                                    "cover_url": result.get("cover_url"),
                                    "total_pages": result.get("total_pages"),
                                    "genre": genre_from_search,
                                }

                            merged_detail = merge_openlibrary_import_data(
                                result, detail, isbn
                            )
                            merged_detail["genre"] = merged_detail.get(
                                "genre"
                            ) or st.session_state.get(FORM_FIELDS["genre"], "")
                            set_form_values(merged_detail)
                            st.session_state["openlibrary_clear_query_pending"] = True
                            st.session_state["openlibrary_last_query"] = ""
                            st.session_state["openlibrary_results"] = []
                            st.session_state["openlibrary_expanded"] = False
                            st.session_state["openlibrary_import_notice"] = (
                                "Book details imported. Continue below in the "
                                "Add Book form."
                            )
                            st.rerun()
                        except RuntimeError as exc:
                            if show_openlibrary_timeout(str(exc)):
                                st.info(
                                    "Open Library timed out while importing. "
                                    "Please try again."
                                )
                            else:
                                st.error(str(exc))
                else:
                    card_col, body_col, action_col = st.columns([1.1, 2.4, 1.1])
                    with card_col:
                        st.image(
                            cover_image_source(
                                result.get("title", "Book"), result.get("cover_url")
                            ),
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
                        if genre_from_search:
                            st.caption(f"Genre: {genre_from_search}")
                    with action_col:
                        unique_suffix = isbn or f"{result.get('title', 'book')}_{idx}"
                        if st.button(
                            "Use This Book",
                            key=f"openlibrary_import_{unique_suffix}",
                            width="stretch",
                        ):
                            try:
                                if isbn:
                                    with st.spinner("Importing book details..."):
                                        detail = api_request(
                                            "GET", f"/openlibrary/book/{isbn}"
                                        )
                                else:
                                    detail = {
                                        "title": result.get("title") or "",
                                        "author": result.get("author") or "",
                                        "isbn": None,
                                        "cover_url": result.get("cover_url"),
                                        "total_pages": result.get("total_pages"),
                                        "genre": genre_from_search,
                                    }

                                merged_detail = merge_openlibrary_import_data(
                                    result, detail, isbn
                                )
                                merged_detail["genre"] = merged_detail.get(
                                    "genre"
                                ) or st.session_state.get(FORM_FIELDS["genre"], "")
                                set_form_values(merged_detail)
                                st.session_state["openlibrary_clear_query_pending"] = (
                                    True
                                )
                                st.session_state["openlibrary_last_query"] = ""
                                st.session_state["openlibrary_results"] = []
                                st.session_state["openlibrary_expanded"] = False
                                st.session_state["openlibrary_import_notice"] = (
                                    "Book details imported. Continue below in the "
                                    "Add Book form."
                                )
                                st.rerun()
                            except RuntimeError as exc:
                                if show_openlibrary_timeout(str(exc)):
                                    st.info(
                                        "Open Library timed out while importing. "
                                        "Please try again."
                                    )
                                else:
                                    st.error(str(exc))

import_notice = st.session_state.pop("openlibrary_import_notice", None)
if import_notice:
    st.success(import_notice)

preview_cover = st.session_state.get(FORM_FIELDS["cover_url"], "")
preview_title = st.session_state.get(FORM_FIELDS["title"], "Book Cover")
if compact_layout:
    st.image(cover_image_source(preview_title, preview_cover), width="stretch")
    title_value = str(st.session_state.get(FORM_FIELDS["title"], "") or "").strip()
    author_value = str(st.session_state.get(FORM_FIELDS["author"], "") or "").strip()
    completion_ratio = (int(bool(title_value)) + int(bool(author_value))) / 2
    st.progress(completion_ratio)
    st.caption("Required fields: Title and Author")

    with st.form("book_form", clear_on_submit=False):
        st.text_input("Title", key=FORM_FIELDS["title"], placeholder="Atomic Habits")
        st.text_input("Author", key=FORM_FIELDS["author"], placeholder="James Clear")
        field_col_1, field_col_2 = st.columns(2)
        with field_col_1:
            st.text_input(
                "ISBN",
                key=FORM_FIELDS["isbn"],
                placeholder="9780307465351",
            )
        with field_col_2:
            st.text_input(
                "Total Pages",
                key=FORM_FIELDS["total_pages"],
                placeholder="320",
            )
        field_col_3, field_col_4 = st.columns(2)
        with field_col_3:
            st.text_input("Genre", key=FORM_FIELDS["genre"], placeholder="Self-help")
        with field_col_4:
            st.text_input(
                "Cover URL", key=FORM_FIELDS["cover_url"], placeholder="https://..."
            )

        if not is_edit_mode:
            st.checkbox("Want to add another book", key="book_form_add_another")

        submit_label = "Save Changes" if is_edit_mode else "Add Book"
        submitted = st.form_submit_button(submit_label, width="stretch", type="primary")

    if submitted:
        try:
            payload = get_form_payload()
        except ValueError as exc:
            st.error(str(exc) or "Please review the form values.")
            st.stop()

        if not payload["title"] or not payload["author"]:
            st.error("Title and author are required.")
        else:
            try:
                with st.spinner("Saving book..."):
                    if is_edit_mode:
                        saved_book = api_request(
                            "PUT", f"/books/{editing_book_id}", json=payload
                        )
                    else:
                        saved_book = api_request("POST", "/books/", json=payload)
                handle_post_save(int(saved_book["id"]), is_edit_mode)
            except RuntimeError as exc:
                st.error(str(exc))
else:
    preview_col, form_col = st.columns([1.1, 1.9])

    with preview_col:
        st.image(cover_image_source(preview_title, preview_cover), width="stretch")

    with form_col:
        title_value = str(st.session_state.get(FORM_FIELDS["title"], "") or "").strip()
        author_value = str(
            st.session_state.get(FORM_FIELDS["author"], "") or ""
        ).strip()
        completion_ratio = (int(bool(title_value)) + int(bool(author_value))) / 2
        st.progress(completion_ratio)
        st.caption("Required fields: Title and Author")

        with st.form("book_form", clear_on_submit=False):
            st.text_input(
                "Title", key=FORM_FIELDS["title"], placeholder="Atomic Habits"
            )
            st.text_input(
                "Author", key=FORM_FIELDS["author"], placeholder="James Clear"
            )
            field_col_1, field_col_2 = st.columns(2)
            with field_col_1:
                st.text_input(
                    "ISBN",
                    key=FORM_FIELDS["isbn"],
                    placeholder="9780307465351",
                )
            with field_col_2:
                st.text_input(
                    "Total Pages",
                    key=FORM_FIELDS["total_pages"],
                    placeholder="320",
                )
            field_col_3, field_col_4 = st.columns(2)
            with field_col_3:
                st.text_input(
                    "Genre", key=FORM_FIELDS["genre"], placeholder="Self-help"
                )
            with field_col_4:
                st.text_input(
                    "Cover URL", key=FORM_FIELDS["cover_url"], placeholder="https://..."
                )

            if not is_edit_mode:
                st.checkbox("Want to add another book", key="book_form_add_another")

            submit_label = "Save Changes" if is_edit_mode else "Add Book"
            submitted = st.form_submit_button(
                submit_label, width="stretch", type="primary"
            )

        if submitted:
            try:
                payload = get_form_payload()
            except ValueError as exc:
                st.error(str(exc) or "Please review the form values.")
                st.stop()

            if not payload["title"] or not payload["author"]:
                st.error("Title and author are required.")
            else:
                try:
                    with st.spinner("Saving book..."):
                        if is_edit_mode:
                            saved_book = api_request(
                                "PUT", f"/books/{editing_book_id}", json=payload
                            )
                        else:
                            saved_book = api_request("POST", "/books/", json=payload)
                    handle_post_save(int(saved_book["id"]), is_edit_mode)
                except RuntimeError as exc:
                    st.error(str(exc))
