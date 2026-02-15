"""
Pytest fixtures for CAIRE tests.

Uses an in-memory SQLite DB for speed and isolation.
StaticPool keeps a single connection so the :memory: database (and tables) persist.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app

TEST_DB = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh in-memory DB and tables per test."""
    test_engine = create_engine(
        TEST_DB,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # single connection so :memory: DB and tables persist
    )
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


@pytest.fixture
def client(db_engine):
    """FastAPI TestClient with test DB."""
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
