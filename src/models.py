from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    books = relationship("Book", back_populates="owner", cascade="all, delete")

class Book(Base):
    __tablename__ = 'books'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    isbn = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    total_pages = Column(Integer, nullable=True)
    cover_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    owner = relationship("User", back_populates="books")
    progress = relationship("Progress", back_populates="book", uselist=False, cascade="all, delete")

class Progress(Base):
    __tablename__ = 'progress'

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False, default='want_to_read')
    pages_read = Column(Integer, nullable=False, default=0)
    rating = Column(Integer, nullable=True)
    notes = Column(String, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    book = relationship("Book", back_populates="progress")