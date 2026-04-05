from src.services.auth_service import create_jwt_token
from jose import jwt
import os


def test_jwt_token_contains_email():
    token = create_jwt_token("user@test.com")
    payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
    assert payload["sub"] == "user@test.com"


def test_jwt_token_has_expiry():
    token = create_jwt_token("user@test.com")
    payload = jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])
    assert "exp" in payload


def test_password_is_hashed():
    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = pwd_context.hash("mypassword")
    assert hashed != "mypassword"
    assert pwd_context.verify("mypassword", hashed)
