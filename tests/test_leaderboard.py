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
    
    # Assert real submission is in the list
    assert any(s["id"] == sub.id for s in subs)
    
    # Assert sample submission is NOT in the list
    assert not any(s["id"] == sub_sample.id for s in subs)
