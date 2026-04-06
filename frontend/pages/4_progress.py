from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import streamlit as st

from shared import (
    API_TO_UI_STATUS,
    UI_TO_API_STATUS,
    api_request,
    build_book_options,
    configure_page,
    format_rating,
    get_book_status,
    get_progress_value,
    render_empty_state,
    render_hero,
    render_sidebar,
    require_auth,
)


def sync_progress_state(book_id: int, total_pages: int, progress: dict[str, object]) -> None:
    st.session_state["progress_loaded_book_id"] = book_id
    st.session_state["progress_status_ui"] = API_TO_UI_STATUS.get(progress.get("status", "not_started"), "want_to_read")
    st.session_state["progress_current_page"] = min(int(progress.get("current_page") or 0), total_pages)
    st.session_state["progress_rating"] = int(progress.get("rating") or 0)
    st.session_state["progress_notes"] = progress.get("notes") or ""
    st.session_state["progress_snapshot"] = {
        "status_ui": st.session_state["progress_status_ui"],
        "current_page": st.session_state["progress_current_page"],
        "rating": st.session_state["progress_rating"],
        "notes": st.session_state["progress_notes"],
    }


def apply_status_to_pages(status_ui: str, current_page: int, total_pages: int) -> int:
    if total_pages <= 0:
        return 0
    if status_ui == "want_to_read":
        return 0
    if status_ui == "finished":
        return total_pages
    return max(1, min(current_page or 1, total_pages))


configure_page("Progress")
require_auth()
render_sidebar("pages/4_progress.py")
render_hero(
    "Reading Progress",
    "Pick a book, update your pages, notes, and rating, and watch the reading summary refresh underneath.",
    kicker="Progress Tracker",
)

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
    "Choose a book",
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
                json={"status": UI_TO_API_STATUS["want_to_read"], "current_page": 0, "rating": None, "notes": ""},
            )
        selected_book["progress"] = progress
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

if st.session_state.get("progress_loaded_book_id") != selected_book_id:
    sync_progress_state(selected_book_id, safe_total_pages, progress)

status_ui = st.radio(
    "Reading status",
    options=["want_to_read", "reading", "finished"],
    horizontal=True,
    key="progress_status_ui",
    format_func=lambda value: {
        "want_to_read": "Want to Read",
        "reading": "Reading",
        "finished": "Finished",
    }[value],
)

if safe_total_pages > 0:
    pages_read = st.slider(
        "Pages read",
        min_value=0,
        max_value=safe_total_pages,
        key="progress_current_page",
    )
else:
    st.session_state["progress_current_page"] = 0
    pages_read = 0
    st.caption("Set total pages on the Add/Edit page to unlock page-by-page tracking.")

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

current_payload = {
    "status_ui": status_ui,
    "current_page": int(pages_read),
    "rating": int(rating_value),
    "notes": notes_value,
}

snapshot = st.session_state.get("progress_snapshot")
if snapshot != current_payload:
    patched_page = apply_status_to_pages(status_ui, int(pages_read), safe_total_pages)

    try:
        with st.spinner("Saving progress..."):
            updated_progress = api_request(
                "PATCH",
                f"/books/{selected_book_id}/progress",
                json={
                    "status": UI_TO_API_STATUS[status_ui],
                    "current_page": patched_page,
                    "rating": None if int(rating_value) == 0 else int(rating_value),
                    "notes": notes_value or None,
                },
            )
        st.session_state["progress_loaded_book_id"] = None
        st.session_state["progress_snapshot"] = None
        st.toast("Progress updated.")
        st.rerun()
    except RuntimeError as exc:
        st.error(str(exc))

if not real_total_pages:
    st.info("This book has no total page count yet, so the slider can only stay at zero until you edit the book details.")

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

metric_cols = st.columns(5)
metric_cols[0].metric("Total books", stats_total)
metric_cols[1].metric("Currently reading", stats_reading)
metric_cols[2].metric("Finished", stats_finished)
metric_cols[3].metric("Want to read", stats_want)
metric_cols[4].metric("Average rating", average_rating if ratings else "N/A")
