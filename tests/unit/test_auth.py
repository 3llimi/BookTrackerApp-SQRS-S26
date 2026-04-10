import os
from uuid import uuid4

import pytest
from fastapi import HTTPException
from jose import jwt

from src.services.auth_service import authenticate_user, create_jwt_token, create_user


def _unique_email(prefix: str = "auth") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@test.com"


def test_create_user_hashes_password(db_session):
    email = _unique_email()

    user = create_user(
        db_session,
        username="reader-1",
        email=email,
        password="password123",
    )

    assert user.id is not None
    assert user.email == email
    assert user.password_hash != "password123"


def test_create_user_duplicate_email_returns_409(db_session):
    email = _unique_email()

    create_user(
        db_session,
        username="reader-2",
        email=email,
        password="password123",
    )

    with pytest.raises(HTTPException) as exc:
        create_user(
            db_session,
            username="reader-3",
            email=email,
            password="password123",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Email already registered"


def test_create_user_duplicate_username_returns_409(db_session):
    username = f"shared-{uuid4().hex[:6]}"

    create_user(
        db_session,
        username=username,
        email=_unique_email("first"),
        password="password123",
    )

    with pytest.raises(HTTPException) as exc:
        create_user(
            db_session,
            username=username,
            email=_unique_email("second"),
            password="password123",
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Username already taken"


def test_authenticate_user_success(db_session):
    email = _unique_email()
    create_user(
        db_session,
        username="reader-4",
        email=email,
        password="password123",
    )

    user = authenticate_user(db_session, email=email, password="password123")

    assert user.email == email


def test_authenticate_user_invalid_password_returns_401(db_session):
    email = _unique_email()
    create_user(
        db_session,
        username="reader-5",
        email=email,
        password="password123",
    )

    with pytest.raises(HTTPException) as exc:
        authenticate_user(db_session, email=email, password="wrong-password")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password"


def test_authenticate_user_unknown_email_returns_401(db_session):
    with pytest.raises(HTTPException) as exc:
        authenticate_user(
            db_session,
            email=_unique_email("missing"),
            password="password123",
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid email or password"


def test_create_jwt_token_contains_sub_and_exp():
    token = create_jwt_token("jwt-user@test.com")

    secret = os.getenv("JWT_SECRET") or "book-tracker-dev-secret-change-me"
    payload = jwt.decode(token, secret, algorithms=["HS256"])

    assert payload["sub"] == "jwt-user@test.com"
    assert "exp" in payload
