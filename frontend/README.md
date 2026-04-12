# Frontend README - Book Tracker (Streamlit)

## Overview

The frontend is a Streamlit application that communicates with the FastAPI backend via HTTP.
It covers authentication, book management (add / view / edit / delete), reading-progress tracking, and search/filtering.

All API calls must include the `Authorization: Bearer <token>` header.
JWT is stored in `st.session_state["token"]` and cleared on logout.

### Theme Modes

Run the frontend in Light Mode:

```bash
poetry run streamlit run --theme.base light
```

Run the frontend in Dark Mode:

```bash
poetry run streamlit run --theme.base dark
```

---

## Screens

### Screen 1 - Auth page (`pages/0_login.py`)

Entry point for unauthenticated users.

**Components**

| Component | Implementation | Notes |
|---|---|---|
| Login / Register switcher | `st.tabs(["Login", "Register"])` | Avoids a separate page |
| Email input | `st.text_input("Email")` | Required |
| Password input | `st.text_input("Password", type="password")` | Required, masked |
| Confirm password | `st.text_input("Confirm password", type="password")` | Register tab only |
| Submit button | `st.form_submit_button("Login")` / `st.form_submit_button("Create account")` | One per tab |
| Inline error | `st.error("...")` | Shown below the form on failure |

**UX rules**

- Show errors inline below the form, not as floating toasts.
- On successful login, store the JWT and redirect using `st.switch_page("pages/1_my_books.py")`.
- Never expose the raw JWT in the UI.

---

### Screen 2 - Book list (`pages/1_my_books.py`) - Main view

Primary collection view.

**Components**

| Component | Implementation | Notes |
|---|---|---|
| Top actions | `st.columns([3, 1])` | Primary action button on the right |
| Result count | `st.write(...)` or `st.caption(...)` | Updates after refresh |
| Book cards grid | `st.columns(3)` | See Book Card spec below |
| Add book button | `st.button("Add a new book")` | Routes to add/edit form |

**UX rules**

- Refresh book data from `GET /books` after state-changing actions.
- Show an empty state with CTA when there are no books.

---

### Screen 3 - Add / Edit form (`pages/2_add_book.py`)

Dedicated page for creating and editing books.

**Components**

| Component | Implementation | Notes |
|---|---|---|
| Title input | `st.text_input("Title")` | Required |
| Author input | `st.text_input("Author")` | Required |
| Genre input | `st.text_input("Genre")` | Optional |
| Total pages | `st.text_input("Total pages")` | Optional, numeric |
| Cover URL | `st.text_input("Cover URL")` | Optional |
| Save button | `st.form_submit_button("Add Book" / "Save Changes")` | Calls POST or PUT |

**UX rules**

- In edit mode, pre-fill all fields from the selected book object.
- Validate required fields and numeric page input before submit.

---

### Screen 4 - Search (`pages/3_search.py`)

Search and filter books with query + sidebar filters.

**Components**

| Component | Implementation | Notes |
|---|---|---|
| Search bar | `st.text_input("Search books")` | Partial match |
| Genre filter | `st.selectbox("Genre", [...])` | Case-insensitive partial match |
| Author filter | `st.selectbox("Author", [...])` | Case-insensitive partial match |
| Status filter | `st.selectbox("Status", [...])` | Exact match |
| Sort controls | `st.selectbox(...)` | Sort field and order |
| Result count | `st.write("... result(s)")` | Updates per filter/query |

---

### Screen 5 - Progress tracker (`pages/4_progress.py`)

Track reading state, page progress, rating, and notes.

**Components**

| Component | Implementation | Notes |
|---|---|---|
| Book selector | `st.selectbox("Choose a book", ...)` | Select target book |
| Status selector | `st.radio(...)` | Want to Read / Reading / Finished |
| Pages read slider | `st.slider(...)` | Enabled when total pages > 0 |
| Rating selector | `st.select_slider(...)` | 0-5 |
| Notes box | `st.text_area(...)` | Free text |
| Metrics row | `st.columns(...).metric(...)` | Library summary |

---

## UI Components

### Book card

Rendered inside `st.columns(3)` on the book list screen.

```text
+-----------------------------+
| The Hitchhiker's Guide      |
| Douglas Adams               |
| [Sci-Fi]                    |
| [########----] 62%          |
| Status: reading             |
|              [Edit] [Delete]|
+-----------------------------+
```

### Progress tracker example

```python
total = st.number_input("Total pages", min_value=0, value=book.total_pages)
current = st.slider(
    "Current page",
    0,
    max(total, 1),
    value=book.current_page,
    disabled=(total == 0),
)
pct = (current / total * 100) if total > 0 else 0
st.metric("Progress", f"{pct:.0f}%")
```

### Search and filter bar example

```python
query = st.text_input("Search title or author")
genre = st.selectbox("Genre", ["All", "Fantasy", "Sci-Fi", ...])
status = st.selectbox("Status", ["All", "not_started", "reading", "completed"])

params = {}
if query:
    params["title"] = query
if genre != "All":
    params["genre"] = genre
if status != "All":
    params["status"] = status

books = api_get("/books", params=params)
st.caption(f"{len(books)} book{'s' if len(books) != 1 else ''}")
```

The backend handles partial matching on title, author, and genre, and exact matching on status.

---

## Session and auth state

```python
# At the top of every protected page
if "token" not in st.session_state:
    st.switch_page("pages/0_login.py")
    st.stop()

# Helper for all API calls
def api_get(path, params=None):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    r = requests.get(f"{BASE_URL}{path}", headers=headers, params=params)
    if r.status_code == 401:
        st.session_state.clear()
        st.switch_page("pages/0_login.py")
        st.stop()
    return r.json()

# Logout
if st.button("Logout"):
    st.session_state.clear()
    st.switch_page("pages/0_login.py")
```

---

## UX happy path

```text
Land on Login page
  -> Register or login
  -> JWT saved to st.session_state["token"]
  -> Redirect to My Books
  -> Browse books
  -> Open Add Book
  -> Fill form
  -> Save -> POST /books
  -> New card appears
  -> Edit an existing book
  -> Track reading progress
  -> Save -> PUT/PATCH endpoints
  -> UI updates in place
```
