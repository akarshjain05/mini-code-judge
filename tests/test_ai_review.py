import pytest
from unittest.mock import AsyncMock, patch
from app.models.submission import Submission
from app.models.problem import Problem
from app.models.user import User

@pytest.fixture
def setup_data(db_session, auth_token):
    user = db_session.query(User).filter(User.username == "akarsh").first()
    problem = Problem(
        title="AI Problem",
        description="Desc",
        difficulty="easy",
    )
    db_session.add(problem)
    db_session.commit()
    db_session.refresh(problem)

    sub = Submission(
        user_id=user.id,
        problem_id=problem.id,
        code="print(1)",
        language="python",
        verdict="wrong_answer",
        status="done",
        is_sample_only=False
    )
    db_session.add(sub)
    db_session.commit()
    db_session.refresh(sub)
    return user, problem, sub

@patch("app.routers.ai_review.GEMINI_API_KEY", "test_key")
@patch("app.routers.ai_review._call_gemini", new_callable=AsyncMock)
def test_ai_review_success(mock_call_gemini, client, auth_headers, setup_data):
    user, problem, sub = setup_data

    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "## Complexity\nO(1)\n## What Went Wrong\nWrong answer"}]
                }
            }
        ]
    }
    mock_call_gemini.return_value = mock_resp

    resp = client.post(f"/submissions/{sub.id}/ai-review", headers=auth_headers)
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is False
    assert "O(1)" in data["review"]

    # Test caching - should return exactly the same text but cached=True without calling API
    mock_call_gemini.reset_mock()
    resp2 = client.post(f"/submissions/{sub.id}/ai-review", headers=auth_headers)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["cached"] is True
    assert "O(1)" in data2["review"]
    mock_call_gemini.assert_not_called()

def test_ai_review_unauthorized_user(client, setup_data):
    user, problem, sub = setup_data
    from tests.conftest import register_and_login_helper
    user2_token = register_and_login_helper(client, "user2", "password123")
    
    resp = client.post(f"/submissions/{sub.id}/ai-review", headers={"Authorization": f"Bearer {user2_token}"})
    assert resp.status_code == 403
    assert "Not your submission" in resp.json()["detail"]

def test_ai_review_missing_key(client, auth_headers, setup_data):
    user, problem, sub = setup_data
    # With no key patched, it should default to the environment one which might be empty
    # We explicitly patch it to empty
    with patch("app.routers.ai_review.GEMINI_API_KEY", ""):
        resp = client.post(f"/submissions/{sub.id}/ai-review", headers=auth_headers)
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]
