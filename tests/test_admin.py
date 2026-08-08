import pytest
from app.models.user import User

@pytest.fixture
def admin_token(client, db_session):
    """Register a user, make them admin, return their auth token."""
    from tests.conftest import register_and_login_helper
    token = register_and_login_helper(client, username="adminuser2", password="password123")
    user = db_session.query(User).filter(User.username == "adminuser2").first()
    user.is_admin = True
    db_session.commit()
    return token

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_admin_get_users_not_admin(client, auth_headers):
    response = client.get("/admin/users", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access only"

def test_admin_get_users_admin(client, admin_headers):
    response = client.get("/admin/users", headers=admin_headers)
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1  # at least the admin user is there
    # Ensure no sensitive fields like password are leaked
    for u in users:
        assert "password" not in u
        assert "username" in u
        assert "email" in u

def test_admin_get_submissions_not_admin(client, auth_headers):
    response = client.get("/admin/submissions", headers=auth_headers)
    assert response.status_code == 403

def test_admin_get_submissions_admin(client, admin_headers):
    response = client.get("/admin/submissions", headers=admin_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
