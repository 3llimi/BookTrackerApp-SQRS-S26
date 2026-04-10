# BookTrackerApp-SQRS-S26

A personal book collection tracker built with FastAPI, Streamlit, and the Open Library API. Part of the Software Quality, Reliability and Security (SQRS) course (Spring 2026).

## Poetry-First Setup

This project is configured for Poetry dependency management.

### 1) Install dependencies

```bash
poetry install
```

### 2) Run the FastAPI backend

```bash
poetry run uvicorn src.main:app --reload
```

### 3) Run the Streamlit frontend

```bash
poetry run streamlit run
```

Or explicitly target the frontend entry file:

```bash
poetry run streamlit run frontend/app.py
```

### 4) Theme Modes (Light and Dark)

Run Light Mode:

```bash
poetry run streamlit run --theme.base light
```

Run Dark Mode:

```bash
poetry run streamlit run --theme.base dark
```

The frontend expects the backend at http://localhost:8000.

## Useful Poetry commands

```bash
poetry run pytest
poetry run flake8 src tests frontend
poetry run black src tests frontend
```

## Optional: export a requirements file

If you need a pip-compatible requirements file for another environment:

```bash
poetry export -f requirements.txt --output requirements.txt --without-hashes
```
