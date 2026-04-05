from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.schemas import AuthLogin, AuthRegister, UserOut
from src.services.auth_service import create_user, authenticate_user, create_jwt_token
from src.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


# POST /api/v1/auth/register
@router.post("/register", response_model=UserOut, status_code=201)
def register(user_in: AuthRegister, db: Session = Depends(get_db)):
    username = user_in.username or user_in.email
    user = create_user(
        db, username=username, email=user_in.email, password=user_in.password
    )
    return user


# POST /api/v1/auth/login
@router.post("/login")
def login(user_in: AuthLogin, db: Session = Depends(get_db)):
    user = authenticate_user(db, email=user_in.email, password=user_in.password)
    token = create_jwt_token(email=user.email)
    return {"access_token": token, "token_type": "bearer"}
