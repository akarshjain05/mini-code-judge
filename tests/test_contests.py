import pytest
from datetime import datetime, timezone, timedelta
from app.models.problem import Problem
from app.models.user import User

@pytest.fixture
def setup_problem(db_session):
    problem = Problem(
        title="Test Problem",
        description="Test Description",
        difficulty="easy",
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)
    return problem

def test_create_contest_unauthorized(client):
    resp = client.post("/contests", json={
        "title": "My Contest",
        "starts_at": datetime.now(timezone.utc).isoformat(),
        "problem_ids": [1]
    })
    assert resp.status_code == 401

def test_create_contest(client, auth_headers, setup_problem):
    future_start = datetime.now(timezone.utc) + timedelta(minutes=10)
    resp = client.post("/contests", json={
        "title": "My Contest",
        "description": "Test",
        "starts_at": future_start.isoformat(),
        "problem_ids": [setup_problem.id],
        "points_per_problem": [100],
        "is_public": True,
        "duration_minutes": 60
    }, headers=auth_headers)
    assert resp.status_code == 201
    assert "invite_code" in resp.json()
    assert resp.json()["title"] == "My Contest"

def test_list_contests(client, auth_headers, setup_problem):
    # Ensure there's a contest
    test_create_contest(client, auth_headers, setup_problem)
    
    resp = client.get("/contests", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["title"] == "My Contest"
    assert "is_joined" in data[0]

def test_join_contest(client, auth_headers, setup_problem):
    # Create contest
    resp = client.post("/contests", json={
        "title": "Join Me",
        "starts_at": datetime.now(timezone.utc).isoformat(),
        "problem_ids": [setup_problem.id],
    }, headers=auth_headers)
    invite_code = resp.json()["invite_code"]

    # Different user joins
    from tests.conftest import register_and_login_helper
    user2_token = register_and_login_helper(client, "user2", "password123")
    
    resp_join = client.post(f"/contests/join/{invite_code}", headers={"Authorization": f"Bearer {user2_token}"})
    assert resp_join.status_code == 200
    assert "Joined successfully" in resp_join.json()["message"]

def test_get_leaderboard(client, auth_headers, setup_problem):
    resp = client.post("/contests", json={
        "title": "Leaderboard Contest",
        "starts_at": datetime.now(timezone.utc).isoformat(),
        "problem_ids": [setup_problem.id],
    }, headers=auth_headers)
    contest_id = resp.json()["id"]

    resp_lb = client.get(f"/contests/{contest_id}/leaderboard", headers=auth_headers)
    assert resp_lb.status_code == 200
    assert isinstance(resp_lb.json(), list)
