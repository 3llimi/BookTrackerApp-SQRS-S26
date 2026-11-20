from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from shared import (  # noqa: E402
    API_TO_UI_STATUS,
    UI_TO_API_STATUS,
    api_request,
    build_book_options,
    configure_page,
    format_rating,
    get_book_status,
    get_progress_value,
    is_compact_layout,
    render_empty_state,
    render_hero,
    render_sidebar,
    require_auth,
)

STATUS_UI_LABELS = {
    "want_to_read": "Want to Read",
    "reading": "Reading",
    "finished": "Finished",
}

# Widget-backed keys. Streamlit forgets a widget's value once its page is left, so
# the page checks for these before trusting the "already loaded" marker.
PROGRESS_WIDGET_KEYS = (
    "progress_status_ui",
    "progress_current_page",
    "progress_rating",
    "progress_notes",
)


def apply_status_to_pages(status_ui: str, current_page: int, total_pages: int) -> int:
    """Return the page count that matches a status the reader just picked."""
    current_page = int(current_page or 0)
    if status_ui == "want_to_read":
        return 0
    if total_pages <= 0:
        return max(current_page, 1)
    if status_ui == "finished":
        return total_pages
    # "Reading": keep the reader's place, but never sit on page 0 or the last page.
    return max(1, min(current_page, total_pages - 1)) if total_pages > 1 else 1


def derive_status_ui_from_pages(current_page: int, total_pages: int) -> str:
    if total_pages <= 0:
        return "reading" if current_page > 0 else "want_to_read"
    if current_page <= 0:
        return "want_to_read"
    if current_page >= total_pages:
        return "finished"
    return "reading"


def sync_progress_state(
    signature: tuple[int, int], total_pages: int, progress: dict[str, object]
) -> None:
    raw_current_page = max(int(progress.get("current_page") or 0), 0)
    current_page = min(raw_current_page, total_pages) if total_pages > 0 else (
        raw_current_page
    )
    status_ui = API_TO_UI_STATUS.get(
        str(progress.get("status") or "not_started"), "want_to_read"
    )
    if status_ui == "finished" and total_pages <= 0:
        status_ui = "reading"
    current_page = apply_status_to_pages(status_ui, current_page, total_pages)
    status_ui = derive_status_ui_from_pages(current_page, total_pages)

    st.session_state["progress_loaded_sig"] = signature
    st.session_state["progress_total_pages"] = total_pages
    st.session_state["progress_status_ui"] = status_ui
    st.session_state["progress_current_page"] = current_page
    st.session_state["progress_rating"] = int(progress.get("rating") or 0)
    st.session_state["progress_notes"] = progress.get("notes") or ""
    st.session_state["progress_snapshot"] = {
        "status_ui": status_ui,
        "current_page": current_page,
        "rating": st.session_state["progress_rating"],
        "notes": st.session_state["progress_notes"],
    }


def on_status_change() -> None:
    """The reader picked a status: move the page counter to match it."""
    total_pages = int(st.session_state.get("progress_total_pages", 0) or 0)
    pages = apply_status_to_pages(
        st.session_state["progress_status_ui"],
        st.session_state.get("progress_current_page", 0),
        total_pages,
    )
    st.session_state["progress_current_page"] = pages
    st.session_state["progress_status_ui"] = derive_status_ui_from_pages(
        pages, total_pages
    )


def on_pages_change() -> None:
    """The reader moved the page counter: keep the status in step with it."""
    total_pages = int(st.session_state.get("progress_total_pages", 0) or 0)
    st.session_state["progress_status_ui"] = derive_status_ui_from_pages(
        int(st.session_state.get("progress_current_page", 0) or 0), total_pages
    )


def discard_changes() -> None:
    snapshot = st.session_state.get("progress_snapshot")
    if not snapshot:
        return
    st.session_state["progress_status_ui"] = snapshot["status_ui"]
    st.session_state["progress_current_page"] = int(snapshot["current_page"])
    st.session_state["progress_rating"] = int(snapshot["rating"])
    st.session_state["progress_notes"] = snapshot["notes"]
    st.session_state["progress_notice"] = "Changes discarded."


def render_metrics(items: list[tuple[str, object]], per_row: int) -> None:
    for start in range(0, len(items), per_row):
        row = items[start : start + per_row]
        for column, (label, value) in zip(st.columns(per_row), row):
            column.metric(label, value)


configure_page("Progress")
require_auth()
render_sidebar("pages/4_progress.py")
render_hero(
    "Reading Progress",
    (
        "Choose a book, update pages, notes, and rating, and see your reading "
        "summary refresh instantly."
    ),
    kicker="Progress Tracker",
)

compact_layout = is_compact_layout()

progress_notice = st.session_state.pop("progress_notice", None)
if progress_notice:
    st.success(progress_notice)

try:
    with st.spinner("Loading your books..."):
        books = api_request(
            "GET",
            "/books/",
            params={"limit": 200, "sort": "title", "order": "asc"},
        )
except RuntimeError as exc:
    st.error(str(exc))
    st.stop()

if not books:
    render_empty_state(
        "You need at least one book first",
        "Add a book before opening the progress tracker.",
    )
    st.stop()

book_labels = {book_id: label for label, book_id in build_book_options(books)}
book_ids = list(book_labels)

selected_book_id = st.session_state.get("selected_book_id")
if selected_book_id not in book_ids:
    selected_book_id = book_ids[0]

selected_book_id = st.selectbox(
    "Choose a Book",
    book_ids,
    index=book_ids.index(selected_book_id),
    format_func=lambda book_id: book_labels[book_id],
)
st.session_state["selected_book_id"] = selected_book_id

selected_book = next(book for book in books if int(book["id"]) == int(selected_book_id))
safe_total_pages = max(int(selected_book.get("total_pages") or 0), 0)
progress = selected_book.get("progress")

if progress is None:
    try:
        with st.spinner("Preparing progress tracking..."):
            progress = api_request(
                "POST",
                f"/books/{selected_book_id}/progress",
                json={
                    "status": UI_TO_API_STATUS["want_to_read"],
                    "current_page": 0,
                    "rating": None,
                    "notes": "",
                },
            )
        selected_book["progress"] = progress
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

# Reload the form when the book (or its page count) changed, or when Streamlit
# dropped the widget values because the reader left this page and came back.
signature = (int(selected_book_id), safe_total_pages)
if st.session_state.get("progress_loaded_sig") != signature or any(
    key not in st.session_state for key in PROGRESS_WIDGET_KEYS
):
    sync_progress_state(signature, safe_total_pages, progress)

status_options = ["want_to_read", "reading"]
if safe_total_pages > 0:
    status_options.append("finished")

status_ui = st.radio(
    "Reading Status",
    options=status_options,
    horizontal=True,
    key="progress_status_ui",
    format_func=lambda value: STATUS_UI_LABELS[value],
    on_change=on_status_change,
)

if safe_total_pages > 0:
    pages_read = int(
        st.slider(
            "Pages Read",
            min_value=0,
            max_value=safe_total_pages,
            key="progress_current_page",
            on_change=on_pages_change,
        )
    )
else:
    pages_read = int(
        st.number_input(
            "Pages Read",
            min_value=0,
            step=1,
            key="progress_current_page",
            on_change=on_pages_change,
        )
    )
    st.caption(
        "This book has no total page count, so progress is tracked by current page "
        "only. Add the page count in Edit Book to unlock the Finished status."
    )

rating_value = int(
    st.select_slider(
        "Rating",
        options=[0, 1, 2, 3, 4, 5],
        key="progress_rating",
        format_func=format_rating,
    )
)

notes_value = st.text_area(
    "Notes",
    key="progress_notes",
    placeholder="Write a few quick thoughts about this book...",
    height=140,
)

completion_pct = (
    min(int(pages_read / safe_total_pages * 100), 100) if safe_total_pages > 0 else 0
)
render_metrics(
    [
        ("Completion", f"{completion_pct}%" if safe_total_pages > 0 else "N/A"),
        (
            "Pages",
            f"{pages_read} / {safe_total_pages}" if safe_total_pages > 0 else pages_read,
        ),
        ("Status", STATUS_UI_LABELS[status_ui]),
    ],
    per_row=2 if compact_layout else 3,
)

current_payload = {
    "status_ui": status_ui,
    "current_page": pages_read,
    "rating": rating_value,
    "notes": notes_value,
}

has_unsaved_changes = st.session_state.get("progress_snapshot") != current_payload

if has_unsaved_changes:
    st.info("You have unsaved progress changes.")

if compact_layout:
    save_clicked = st.button(
        "Save Progress",
        width="stretch",
        type="primary",
        disabled=not has_unsaved_changes,
    )
    st.button(
        "Discard Changes",
        width="stretch",
        type="secondary",
        disabled=not has_unsaved_changes,
        on_click=discard_changes,
    )
else:
    action_col_1, action_col_2 = st.columns(2)
    with action_col_1:
        save_clicked = st.button(
            "Save Progress",
            width="stretch",
            type="primary",
            disabled=not has_unsaved_changes,
        )
    with action_col_2:
        st.button(
            "Discard Changes",
            width="stretch",
            type="secondary",
            disabled=not has_unsaved_changes,
            on_click=discard_changes,
        )

if save_clicked:
    try:
        with st.spinner("Saving progress..."):
            api_request(
                "PATCH",
                f"/books/{selected_book_id}/progress",
                json={
                    "status": UI_TO_API_STATUS[status_ui],
                    "current_page": pages_read,
                    "rating": None if rating_value == 0 else rating_value,
                    "notes": notes_value or None,
                },
            )
        st.session_state["progress_loaded_sig"] = None
        st.session_state["progress_snapshot"] = None
        st.session_state["progress_notice"] = "Progress saved."
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))

st.markdown("#### Library Snapshot")
ratings = [
    get_progress_value(book, "rating")
    for book in books
    if get_progress_value(book, "rating") is not None
]
render_metrics(
    [
        ("Total Books", len(books)),
        (
            "Currently Reading",
            sum(1 for book in books if get_book_status(book) == "reading"),
        ),
        (
            "Finished",
            sum(1 for book in books if get_book_status(book) == "completed"),
        ),
        (
            "Want to Read",
            sum(1 for book in books if get_book_status(book) == "not_started"),
        ),
        ("Average Rating", round(sum(ratings) / len(ratings), 1) if ratings else "N/A"),
    ],
    per_row=2 if compact_layout else 3,
)
