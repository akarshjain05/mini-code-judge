"""
Basic tests for the submission flow.
Run with: pytest tests/

These test the API layer only — the actual code execution
is tested separately by running real submissions.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db

# Use an in-memory SQLite DB for tests — no PostgreSQL needed
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


# Override the real DB with the test DB
app.dependency_overrides[get_db] = override_get_db
Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Drop and recreate tables before each test for isolation."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


def register_and_login(username="akarsh", password="testpass123"):
    """Helper: register a user and return their JWT token."""
    client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@test.com",
        "password": password,
    })
    resp = client.post("/auth/login", data={
        "username": username,
        "password": password,
    })
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


# ── Auth tests ────────────────────────────────────────────────────────────────

def test_register_success():
    resp = client.post("/auth/register", json={
        "username": "akarsh",
        "email": "akarsh@test.com",
        "password": "secret123",
    })
    assert resp.status_code == 201
    assert resp.json()["username"] == "akarsh"
    assert "password" not in resp.json()  # Never leak the hash


def test_register_duplicate_username():
    client.post("/auth/register", json={"username": "akarsh", "email": "a@t.com", "password": "x"})
    resp = client.post("/auth/register", json={"username": "akarsh", "email": "b@t.com", "password": "x"})
    assert resp.status_code == 400


def test_login_wrong_password():
    client.post("/auth/register", json={"username": "akarsh", "email": "a@t.com", "password": "correct"})
    resp = client.post("/auth/login", data={"username": "akarsh", "password": "wrong"})
    assert resp.status_code == 401


# ── Submission validation tests ───────────────────────────────────────────────

def test_submit_requires_login():
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "cpp",
        "code": "int main(){}",
    })
    assert resp.status_code == 401


def test_submit_unsupported_language():
    token = register_and_login()
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "java",   # Not supported yet
        "code": "class Main {}",
    }, headers=auth_headers(token))
    assert resp.status_code == 422  # Pydantic validation error


def test_submit_empty_code():
    token = register_and_login()
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "cpp",
        "code": "   ",   # Only whitespace
    }, headers=auth_headers(token))
    assert resp.status_code == 422


def test_submit_nonexistent_problem():
    token = register_and_login()
    resp = client.post("/submissions", json={
        "problem_id": 9999,
        "language": "cpp",
        "code": "#include<bits/stdc++.h>\nint main(){cout<<42;}",
    }, headers=auth_headers(token))
    assert resp.status_code == 404


def test_health_check():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
