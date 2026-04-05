from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ProgressCreate(BaseModel):
    status: str  # "Want to Read", "Reading", "Read"
    pages_read: Optional[int] = 0
    rating: Optional[int] = None
    notes: Optional[str] = None


class ProgressUpdate(BaseModel):
    status: Optional[str] = None
    pages_read: Optional[int] = None
    rating: Optional[int] = None
    notes: Optional[str] = None


class ProgressOut(BaseModel):
    id: int
    status: str
    pages_read: int
    rating: Optional[int] = None
    notes: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    genre: Optional[str] = None
    total_pages: Optional[int] = None
    cover_url: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    genre: Optional[str] = None
    total_pages: Optional[int] = None
    cover_url: Optional[str] = None


class BookOut(BaseModel):
    id: int
    title: str
    author: str
    isbn: Optional[str] = None
    genre: Optional[str] = None
    total_pages: Optional[int] = None
    cover_url: Optional[str] = None
    created_at: datetime
    progress: Optional[ProgressOut] = None

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class AuthRegister(BaseModel):
    email: str
    password: str
    username: Optional[str] = None


class AuthLogin(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
