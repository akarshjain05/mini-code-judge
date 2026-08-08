import pytest
from app.models.user import User
from app.models.problem import Problem

@pytest.fixture
def admin_token(client, db_session):
    """Register a user, make them admin, return their auth token."""
    from tests.conftest import register_and_login_helper
    token = register_and_login_helper(client, username="adminuser", password="password123")
    user = db_session.query(User).filter(User.username == "adminuser").first()
    user.is_admin = True
    db_session.commit()
    return token

@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

def test_list_problems_empty(client):
    response = client.get("/problems")
    assert response.status_code == 200
    assert response.json() == []

def test_create_problem_not_admin(client, auth_headers):
    payload = {
        "title": "A Problem",
        "description": "Some text",
        "difficulty": "easy"
    }
    response = client.post("/problems", json=payload, headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"

def test_create_problem_admin(client, admin_headers):
    payload = {
        "title": "Admin Problem",
        "description": "Admin text",
        "difficulty": "medium",
        "category": "arrays"
    }
    response = client.post("/problems", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert "id" in data
    
def test_get_problem(client, admin_headers):
    # Create problem first
    payload = {"title": "P1", "description": "D1", "difficulty": "hard"}
    post_res = client.post("/problems", json=payload, headers=admin_headers)
    p_id = post_res.json()["id"]

    # Get problem
    get_res = client.get(f"/problems/{p_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "P1"

def test_update_problem(client, admin_headers):
    # Create problem
    payload = {"title": "P1", "description": "D1"}
    p_id = client.post("/problems", json=payload, headers=admin_headers).json()["id"]

    # Update problem
    update_payload = {"title": "P1_updated", "description": "D1_updated", "difficulty": "medium"}
    update_res = client.put(f"/problems/{p_id}", json=update_payload, headers=admin_headers)
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "P1_updated"

def test_add_test_case(client, admin_headers):
    # Create problem
    payload = {"title": "P1", "description": "D1"}
    p_id = client.post("/problems", json=payload, headers=admin_headers).json()["id"]

    # Add test case
    tc_payload = {"stdin": "1 2\n", "expected": "3\n", "is_sample": True}
    tc_res = client.post(f"/problems/{p_id}/test-cases", json=tc_payload, headers=admin_headers)
    assert tc_res.status_code == 201

    # Get sample tests
    sample_res = client.get(f"/problems/{p_id}/sample-tests")
    assert sample_res.status_code == 200
    data = sample_res.json()
    assert len(data) == 1
    assert data[0]["stdin"] == "1 2\n"
