import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from app.main import app, limiter
from app.routers.auth import limiter as auth_limiter
limiter.enabled = False
auth_limiter.enabled = False
from app.core.database import Base, get_db

# Use an in-memory SQLite DB for tests
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="session")
def client():
    return TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    """Drop and recreate tables before each test for isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

@pytest.fixture
def db_session():
    """Fixture to provide a database session directly to tests."""
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

def register_and_login_helper(client, username="akarsh", password="password123"):
    """Helper: register a user and return their JWT token."""
    with patch("app.routers.auth.send_verification_email"):
        client.post("/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": password,
        })
    # Manually verify the user in the test database
    from app.models.user import User
    db = TestingSession()
    user = db.query(User).filter(User.username == username).first()
    if user:
        user.is_verified = True
        db.commit()
    db.close()

    resp = client.post("/auth/login", data={
        "username": username,
        "password": password,
    })
    return resp.json().get("access_token")

@pytest.fixture
def auth_token(client):
    """Fixture that returns a valid auth token for a verified user."""
    return register_and_login_helper(client)

@pytest.fixture
def auth_headers(auth_token):
    """Fixture that returns headers with a valid auth token."""
    return {"Authorization": f"Bearer {auth_token}"}
