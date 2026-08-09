import pytest
from app.models.submission import Submission
from app.models.user import User

def test_leaderboard_users(client, auth_headers):
    resp = client.get("/leaderboard/users")
    assert resp.status_code == 200
    users = resp.json()
    assert len(users) >= 1
    # Check that our test user is in there
    assert any(u["username"] == "akarsh" for u in users)

def test_leaderboard_submissions_empty(client):
    resp = client.get("/leaderboard/submissions")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_leaderboard_submissions_with_data(client, auth_headers, db_session):
    # Get user id
    user = db_session.query(User).filter(User.username == "akarsh").first()
    
    # Add a mock submission
    sub = Submission(
        user_id=user.id,
        problem_id=1,
        code="print(1)",
        language="python",
        verdict="accepted",
        is_sample_only=False
    )
    db_session.add(sub)
    
    # Add a sample-only submission which should be filtered out
    sub_sample = Submission(
        user_id=user.id,
        problem_id=1,
        code="print(1)",
        language="python",
        verdict="accepted",
        is_sample_only=True
    )
    db_session.add(sub_sample)
    db_session.commit()

    resp = client.get("/leaderboard/submissions")
    assert resp.status_code == 200
    subs = resp.json()
    
    # Assert our test user is in the aggregated list and stats reflect only the real submission
    user_stats = next((s for s in subs if s["username"] == "akarsh"), None)
    assert user_stats is not None
    assert user_stats["total"] == 1
    assert user_stats["accepted"] == 1
    assert "python" in user_stats["langs"]
