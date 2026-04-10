from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Literal
from datetime import datetime


ProgressStatus = Literal["not_started", "reading", "completed"]


class ProgressCreate(BaseModel):
    status: ProgressStatus = "not_started"
    current_page: int = Field(default=0, ge=0)
    rating: Optional[int] = None
    notes: Optional[str] = None


class ProgressUpdate(BaseModel):
    status: Optional[ProgressStatus] = None
    current_page: Optional[int] = Field(default=None, ge=0)
    rating: Optional[int] = None
    notes: Optional[str] = None


class ProgressOut(BaseModel):
    id: int
    status: str
    current_page: int
    rating: Optional[int]
    notes: Optional[str]
    updated_at: datetime
    progress_percentage: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class BookCreate(BaseModel):
    title: str
    author: str
    isbn: Optional[str] = None
    genre: Optional[str] = None
    total_pages: Optional[int] = Field(default=None, ge=0)
    cover_url: Optional[str] = None


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    genre: Optional[str] = None
    total_pages: Optional[int] = Field(default=None, ge=0)
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
    progress_percentage: Optional[float] = None

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
