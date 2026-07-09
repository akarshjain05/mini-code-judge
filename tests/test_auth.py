import pytest
from app.models.user import User
from app.core.redis_client import get_redis
from unittest.mock import patch

# Clear redis before each test to ensure fresh state for rate limiting and lockouts
@pytest.fixture(autouse=True)
def clean_redis():
    get_redis().flushdb()
    yield

@patch("app.routers.auth.send_verification_email")
def test_register_success(mock_send, client, db_session):
    resp = client.post("/auth/register", json={
        "username": "newuser",
        "email": "newuser@test.com",
        "password": "secretpassword123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == "newuser"
    assert "password" not in data

    # Verify it's in the DB and not verified yet
    user = db_session.query(User).filter(User.username == "newuser").first()
    assert user is not None
    assert user.is_verified is False

@patch("app.routers.auth.send_verification_email")
def test_register_duplicate(mock_send, client):
    client.post("/auth/register", json={"username": "dupuser", "email": "a@t.com", "password": "password123"})
    resp = client.post("/auth/register", json={"username": "dupuser", "email": "b@t.com", "password": "password123"})
    assert resp.status_code == 400
    assert "Username already taken" in resp.json()["detail"]

    resp = client.post("/auth/register", json={"username": "dupuser2", "email": "a@t.com", "password": "password123"})
    assert resp.status_code == 400
    assert "Email already registered" in resp.json()["detail"]

@patch("app.routers.auth.send_verification_email")
def test_login_unverified(mock_send, client):
    client.post("/auth/register", json={"username": "unverified", "email": "u@t.com", "password": "password123"})
    resp = client.post("/auth/login", data={"username": "unverified", "password": "password123"})
    assert resp.status_code == 403
    assert "verify your email" in resp.json()["detail"]

@patch("app.routers.auth.send_verification_email")
def test_login_success(mock_send, client, db_session):
    client.post("/auth/register", json={"username": "verified", "email": "v@t.com", "password": "password123"})
    user = db_session.query(User).filter(User.username == "verified").first()
    user.is_verified = True
    db_session.commit()

    resp = client.post("/auth/login", data={"username": "verified", "password": "password123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@patch("app.routers.auth.send_verification_email")
def test_login_wrong_password_lockout(mock_send, client, db_session):
    client.post("/auth/register", json={"username": "lockout", "email": "l@t.com", "password": "password123"})
    
    # 5 wrong attempts
    for i in range(5):
        resp = client.post("/auth/login", data={"username": "lockout", "password": "wrongpassword123"})
        assert resp.status_code == 401
        
    # 6th attempt should return 429 Too Many Requests
    resp = client.post("/auth/login", data={"username": "lockout", "password": "pwd123"})
    assert resp.status_code == 429
    assert "Account locked" in resp.json()["detail"]

@patch("app.routers.auth.send_verification_email")
def test_forgot_password_and_reset(mock_send, client, db_session):
    client.post("/auth/register", json={"username": "forgot", "email": "forgot@t.com", "password": "old_pwd123"})
    
    # Request reset
    from unittest.mock import patch
    with patch("app.routers.auth.send_password_reset_email", return_value=True):
        resp = client.post("/auth/forgot-password", json={"email": "forgot@t.com"})
    assert resp.status_code == 200

    # In a real scenario, an email is sent. For the test, we'll manually generate a token to test the reset endpoint
    user = db_session.query(User).filter(User.email == "forgot@t.com").first()
    from datetime import datetime, timedelta
    from jose import jwt
    from app.core.config import settings
    reset_token = jwt.encode(
        {"sub": str(user.id), "purpose": "password_reset", "exp": datetime.utcnow() + timedelta(minutes=15)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )

    resp = client.post("/auth/reset-password", json={"reset_token": reset_token, "new_password": "new_secret_pwd123"})
    assert resp.status_code == 200
    assert resp.json()["message"] == "Password reset successfully"

    # Verify the new password works
    user.is_verified = True
    db_session.commit()
    resp = client.post("/auth/login", data={"username": "forgot", "password": "new_secret_pwd123"})
    assert resp.status_code == 200
