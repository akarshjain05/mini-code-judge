import pytest
from unittest.mock import patch, MagicMock
from app.models.user import User

@pytest.fixture
def mock_google_verify():
    with patch("app.routers.auth.google_id_token.verify_oauth2_token") as mock_verify:
        yield mock_verify

@pytest.fixture
def mock_github_httpx():
    with patch("app.routers.auth.httpx.post") as mock_post, \
         patch("app.routers.auth.httpx.get") as mock_get:
        yield mock_post, mock_get

def test_google_login_new_user_requires_username(client, mock_google_verify, db_session):
    mock_google_verify.return_value = {
        "sub": "google123",
        "email": "newgoogle@example.com",
        "email_verified": True
    }
    
    resp = client.post("/auth/google", json={"credential": "fake_token"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["needs_setup"] is True
    assert "setup_token" in data

def test_google_login_existing_user(client, mock_google_verify, db_session):
    u = User(username="googleuser", email="existing@example.com", password="", is_verified=True, google_id="g123")
    db_session.add(u)
    db_session.commit()
    
    mock_google_verify.return_value = {
        "sub": "g123",
        "email": "existing@example.com",
        "email_verified": True
    }
    
    resp = client.post("/auth/google", json={"credential": "fake_token"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["needs_setup"] is False

def test_complete_google_signup(client, mock_google_verify, db_session):
    mock_google_verify.return_value = {
        "sub": "google999",
        "email": "finish@example.com",
        "email_verified": True
    }
    
    with patch("app.routers.auth.decode_setup_token") as mock_decode:
        mock_decode.return_value = {"google_id": "google999", "email": "finish@example.com", "purpose": "google_signup"}
        
        resp = client.post("/auth/complete-google-signup", json={
            "setup_token": "fake_token",
            "username": "new_google_guy",
            "password": "password123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        
        u = db_session.query(User).filter_by(username="new_google_guy").first()
        assert u is not None
        assert u.email == "finish@example.com"

def test_github_login_redirect(client):
    with patch("app.routers.auth.settings.GITHUB_CLIENT_ID", "fake_id"):
        resp = client.get("/auth/github", follow_redirects=False)
        assert resp.status_code == 307
        assert "github.com/login/oauth/authorize" in resp.headers["location"]

def test_github_redirect_existing_user(client, mock_github_httpx, db_session):
    mock_post, mock_get = mock_github_httpx
    
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "gh_token"}
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"login": "gh_user", "id": 123}),
        MagicMock(status_code=200, json=lambda: [{"email": "gh@example.com", "primary": True, "verified": True}])
    ]
    
    u = User(username="gh_user", email="gh@example.com", password="", is_verified=True, github_id="123")
    db_session.add(u)
    db_session.commit()
    
    resp = client.get("/auth/github/redirect?code=fake_code", follow_redirects=False)
    assert resp.status_code == 307
    assert "#github-" in resp.headers["location"]

def test_github_redirect_new_user(client, mock_github_httpx, db_session):
    mock_post, mock_get = mock_github_httpx
    
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {"access_token": "gh_token"}
    
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: {"login": "new_gh_user", "id": 999}),
        MagicMock(status_code=200, json=lambda: [{"email": "new_gh@example.com", "primary": True, "verified": True}])
    ]
    
    resp = client.get("/auth/github/redirect?code=fake_code", follow_redirects=False)
    assert resp.status_code == 307
    assert "new_gh_user" in resp.headers["location"]

def test_complete_github_signup(client, db_session):
    with patch("app.routers.auth.decode_setup_token") as mock_decode:
        mock_decode.return_value = {"github_id": "888", "email": "gh_guy@example.com", "purpose": "github_signup"}
        
        resp = client.post("/auth/complete-github-signup", json={
            "setup_token": "fake_temp_token",
            "username": "new_gh_guy_custom"
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()
        
        u = db_session.query(User).filter_by(username="new_gh_guy_custom").first()
        assert u is not None
        assert u.email == "gh_guy@example.com"
        assert u.github_id == "888"
