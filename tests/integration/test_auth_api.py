from uuid import uuid4


def _unique_email(prefix: str = "auth-api") -> str:
    return f"{prefix}-{uuid4().hex[:8]}@test.com"


def test_register_success_defaults_username_to_email(client):
    email = _unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["username"] == email
    assert "password_hash" not in data


def test_register_with_explicit_username(client):
    email = _unique_email("auth-api-user")

    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "username": "reader"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == email
    assert data["username"] == "reader"


def test_register_duplicate_email_returns_409(client):
    email = _unique_email("dup-email")

    first = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    second = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


def test_register_duplicate_username_returns_409(client):
    username = f"shared-{uuid4().hex[:6]}"

    first = client.post(
        "/api/v1/auth/register",
        json={
            "email": _unique_email("dup-user-first"),
            "password": "password123",
            "username": username,
        },
    )
    second = client.post(
        "/api/v1/auth/register",
        json={
            "email": _unique_email("dup-user-second"),
            "password": "password123",
            "username": username,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"] == "Username already taken"


def test_login_success_returns_bearer_token(client):
    email = _unique_email("login-success")

    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )

    assert login_response.status_code == 200
    body = login_response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_invalid_credentials_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": _unique_email("missing"), "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_register_missing_email_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"password": "password123"},
    )

    assert response.status_code == 422


def test_register_missing_password_returns_422(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": _unique_email("missing-password")},
    )

    assert response.status_code == 422
