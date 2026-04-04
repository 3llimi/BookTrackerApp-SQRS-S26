from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.database import Base, engine
from src.routers import books, progress, auth, openlibrary

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    Base.metadata.create_all(bind=engine)
    yield
    # No specific shutdown actions needed

app = FastAPI(
    title="Book Tracker API",
    description="API for tracking book reading progress",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router,       prefix="/api/v1")
app.include_router(progress.router,    prefix="/api/v1")
app.include_router(auth.router,        prefix="/api/v1")
app.include_router(openlibrary.router, prefix="/api/v1")