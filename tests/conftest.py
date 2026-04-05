import pytest

from src.database import Base, engine


@pytest.fixture(autouse=True)
def reset_database():
	Base.metadata.drop_all(bind=engine)
	Base.metadata.create_all(bind=engine)
	yield
	Base.metadata.drop_all(bind=engine)
