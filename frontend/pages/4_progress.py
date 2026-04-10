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
    is_compact_layout,
    get_status_badge,
    get_progress_value,
    render_empty_state,
    render_hero,
    render_sidebar,
    require_auth,
)


def sync_progress_state(
    book_id: int, total_pages: int, progress: dict[str, object]
) -> None:
    raw_current_page = int(progress.get("current_page") or 0)
    current_page = (
        min(raw_current_page, total_pages)
        if total_pages > 0
        else max(raw_current_page, 0)
    )

    st.session_state["progress_loaded_book_id"] = book_id
    st.session_state["progress_status_ui"] = API_TO_UI_STATUS.get(
        progress.get("status", "not_started"), "want_to_read"
    )
    st.session_state["progress_current_page"] = current_page
    st.session_state["progress_current_page_free"] = current_page
    st.session_state["progress_rating"] = int(progress.get("rating") or 0)
    st.session_state["progress_notes"] = progress.get("notes") or ""
    st.session_state["progress_snapshot"] = {
        "status_ui": st.session_state["progress_status_ui"],
        "current_page": current_page,
        "rating": st.session_state["progress_rating"],
        "notes": st.session_state["progress_notes"],
    }


def apply_status_to_pages(status_ui: str, current_page: int, total_pages: int) -> int:
    if total_pages <= 0:
        if status_ui == "want_to_read":
            return 0
        return max(int(current_page or 0), 1)
    if status_ui == "want_to_read":
        return 0
    if status_ui == "finished":
        return total_pages
    return max(1, min(current_page or 1, total_pages))


def derive_status_ui_from_pages(current_page: int, total_pages: int) -> str:
    if total_pages <= 0:
        return "reading" if current_page > 0 else "want_to_read"
    if current_page <= 0:
        return "want_to_read"
    if current_page >= total_pages:
        return "finished"
    return "reading"


def restore_progress_snapshot(snapshot: dict[str, object] | None) -> None:
    if not snapshot:
        return
    st.session_state["progress_status_ui"] = snapshot.get("status_ui", "want_to_read")
    st.session_state["progress_current_page"] = int(snapshot.get("current_page") or 0)
    st.session_state["progress_current_page_free"] = int(
        snapshot.get("current_page") or 0
    )
    st.session_state["progress_rating"] = int(snapshot.get("rating") or 0)
    st.session_state["progress_notes"] = snapshot.get("notes") or ""


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
st.session_state.setdefault("progress_restore_pending", False)

progress_notice = st.session_state.pop("progress_notice", None)
if progress_notice:
    st.success(progress_notice)

try:
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

book_options = build_book_options(books)
label_to_id = dict(book_options)
book_ids = [book_id for _, book_id in book_options]

selected_book_id = st.session_state.get("selected_book_id")
if selected_book_id not in book_ids:
    selected_book_id = book_ids[0]
    st.session_state["selected_book_id"] = selected_book_id

selected_label = st.selectbox(
    "Choose a Book",
    [label for label, _ in book_options],
    index=book_ids.index(selected_book_id),
)
selected_book_id = label_to_id[selected_label]
st.session_state["selected_book_id"] = selected_book_id

selected_book = next(book for book in books if int(book["id"]) == int(selected_book_id))
real_total_pages = int(selected_book.get("total_pages") or 0)
safe_total_pages = real_total_pages if real_total_pages > 0 else 0
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

if st.session_state.get("progress_loaded_book_id") != selected_book_id:
    sync_progress_state(selected_book_id, safe_total_pages, progress)

if st.session_state.pop("progress_restore_pending", False):
    restore_progress_snapshot(st.session_state.get("progress_snapshot"))

auto_status_ui = derive_status_ui_from_pages(
    int(st.session_state.get("progress_current_page", 0) or 0),
    safe_total_pages,
)
if st.session_state.get("progress_status_ui") != auto_status_ui:
    st.session_state["progress_status_ui"] = auto_status_ui

status_ui = st.radio(
    "Reading Status",
    options=["want_to_read", "reading", "finished"],
    horizontal=True,
    key="progress_status_ui",
    format_func=lambda value: {
        "want_to_read": "Want to Read",
        "reading": "Reading",
        "finished": "Finished",
    }[value],
)

status_api = UI_TO_API_STATUS[status_ui]
st.caption(get_status_badge(status_api))

if safe_total_pages > 0:
    pages_read = st.slider(
        "Pages Read",
        min_value=0,
        max_value=safe_total_pages,
        key="progress_current_page",
    )
else:
    st.session_state.setdefault(
        "progress_current_page_free",
        int(st.session_state.get("progress_current_page", 0) or 0),
    )
    pages_read = int(
        st.number_input(
            "Pages Read",
            min_value=0,
            step=1,
            key="progress_current_page_free",
        )
    )
    st.caption(
        (
            "This book has no total page count, so progress is tracked by "
            "current page only."
        )
    )

rating_value = st.select_slider(
    "Rating",
    options=[0, 1, 2, 3, 4, 5],
    key="progress_rating",
    format_func=format_rating,
)

notes_value = st.text_area(
    "Notes",
    key="progress_notes",
    placeholder="Write a few quick thoughts about this book...",
    height=140,
)

completion_pct = (
    int((int(pages_read) / safe_total_pages) * 100) if safe_total_pages > 0 else 0
)
effective_pages = apply_status_to_pages(status_ui, int(pages_read), safe_total_pages)
effective_pct = (
    int((effective_pages / safe_total_pages) * 100) if safe_total_pages > 0 else 0
)
if compact_layout:
    summary_col_1, summary_col_2 = st.columns(2)
    summary_col_1.metric("Completion", f"{effective_pct}%")
    summary_col_2.metric(
        "Pages",
        (
            f"{effective_pages} / {safe_total_pages}"
            if safe_total_pages > 0
            else str(effective_pages)
        ),
    )
    st.metric(
        "Status",
        {
            "want_to_read": "Want to Read",
            "reading": "Reading",
            "finished": "Finished",
        }[status_ui],
    )
else:
    summary_col_1, summary_col_2, summary_col_3 = st.columns(3)
    summary_col_1.metric("Completion", f"{effective_pct}%")
    summary_col_2.metric(
        "Pages",
        (
            f"{effective_pages} / {safe_total_pages}"
            if safe_total_pages > 0
            else str(effective_pages)
        ),
    )
    summary_col_3.metric(
        "Status",
        {
            "want_to_read": "Want to Read",
            "reading": "Reading",
            "finished": "Finished",
        }[status_ui],
    )

current_payload = {
    "status_ui": status_ui,
    "current_page": int(pages_read),
    "rating": int(rating_value),
    "notes": notes_value,
}

snapshot = st.session_state.get("progress_snapshot")
has_unsaved_changes = snapshot != current_payload

if has_unsaved_changes:
    st.info("You have unsaved progress changes.")

if compact_layout:
    save_clicked = st.button(
        "Save Progress",
        width="stretch",
        type="primary",
        disabled=not has_unsaved_changes,
    )
    discard_clicked = st.button(
        "Discard Changes",
        width="stretch",
        type="secondary",
        disabled=not has_unsaved_changes,
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
        discard_clicked = st.button(
            "Discard Changes",
            width="stretch",
            type="secondary",
            disabled=not has_unsaved_changes,
        )

if discard_clicked:
    st.session_state["progress_restore_pending"] = True
    st.session_state["progress_notice"] = "Changes discarded."
    st.rerun()

if save_clicked:
    try:
        with st.spinner("Saving progress..."):
            updated_progress = api_request(
                "PATCH",
                f"/books/{selected_book_id}/progress",
                json={
                    "status": UI_TO_API_STATUS[status_ui],
                    "current_page": effective_pages,
                    "rating": None if int(rating_value) == 0 else int(rating_value),
                    "notes": notes_value or None,
                },
            )
        st.session_state["progress_loaded_book_id"] = None
        st.session_state["progress_snapshot"] = None
        st.session_state["progress_notice"] = "Progress updated."
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))

if not real_total_pages:
    st.info(
        (
            "This book has no total page count yet, so the slider stays at "
            "zero until you update the book details."
        )
    )

stats_total = len(books)
stats_reading = sum(1 for book in books if get_book_status(book) == "reading")
stats_finished = sum(1 for book in books if get_book_status(book) == "completed")
stats_want = sum(1 for book in books if get_book_status(book) == "not_started")
ratings = [
    get_progress_value(book, "rating")
    for book in books
    if get_progress_value(book, "rating") is not None
]
average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0.0

if compact_layout:
    metric_row_1 = st.columns(2)
    metric_row_2 = st.columns(2)
    metric_row_1[0].metric("Total Books", stats_total)
    metric_row_1[1].metric("Currently Reading", stats_reading)
    metric_row_2[0].metric("Finished", stats_finished)
    metric_row_2[1].metric("Want to Read", stats_want)
    st.metric("Average Rating", average_rating if ratings else "N/A")
else:
    top_metric_cols = st.columns(3)
    bottom_metric_cols = st.columns(2)

    top_metric_cols[0].metric("Total Books", stats_total)
    top_metric_cols[1].metric("Currently Reading", stats_reading)
    top_metric_cols[2].metric("Finished", stats_finished)
    bottom_metric_cols[0].metric("Want to Read", stats_want)
    bottom_metric_cols[1].metric("Average Rating", average_rating if ratings else "N/A")
