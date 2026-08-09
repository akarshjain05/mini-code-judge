"""
Basic tests for the submission flow.
Run with: pytest tests/

These test the API layer only — the actual code execution
is tested separately by running real submissions.
"""

def test_submit_requires_login(client):
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "cpp",
        "code": "int main(){}",
    })
    assert resp.status_code == 401


def test_submit_supported_languages(client, auth_headers):
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "java",
        "code": "public class Main { public static void main(String[] a){} }",
    }, headers=auth_headers)
    assert resp.status_code == 404  # problem missing — but language must not be rejected


def test_submit_unsupported_language(client, auth_headers):
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "rust",
        "code": "fn main(){}",
    }, headers=auth_headers)
    assert resp.status_code == 422  # Pydantic validation error


def test_submit_empty_code(client, auth_headers):
    resp = client.post("/submissions", json={
        "problem_id": 1,
        "language": "cpp",
        "code": "   ",   # Only whitespace
    }, headers=auth_headers)
    assert resp.status_code == 422


def test_submit_nonexistent_problem(client, auth_headers):
    resp = client.post("/submissions", json={
        "problem_id": 9999,
        "language": "cpp",
        "code": "#include<bits/stdc++.h>\nint main(){cout<<42;}",
    }, headers=auth_headers)
    assert resp.status_code == 404


def test_health_check(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_submit_and_judge_e2e(client, auth_headers, db_session):
    # 1. Create a problem and test case directly in DB
    from app.models.problem import Problem, TestCase
    from app.models.submission import Submission
    p = Problem(title="Add Two", description="Add a and b", difficulty="easy")
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    tc = TestCase(problem_id=p.id, stdin="5 7\n", expected="12\n", is_sample=True)
    db_session.add(tc)
    db_session.commit()

    # 2. Submit valid Python code
    from unittest.mock import patch
    with patch("app.routers.submissions.Queue"):
        resp = client.post("/submissions", json={
            "problem_id": p.id,
            "language": "python",
            "code": "import sys\nfor line in sys.stdin:\n    a, b = map(int, line.split())\n    print(a + b)\n",
        }, headers=auth_headers)
    assert resp.status_code == 202
    sub_id = resp.json()["id"]

    # 3. Manually run the worker function to judge it synchronously
    from app.worker.judge import judge_submission
    import app.core.database
    from tests.conftest import TestingSession
    
    # Mock SessionLocal so the worker uses the test SQLite DB
    original_session = app.core.database.SessionLocal
    app.core.database.SessionLocal = TestingSession
    try:
        judge_submission(sub_id)
    finally:
        app.core.database.SessionLocal = original_session

    # 4. Verify it was accepted
    db_session.expire_all()
    sub = db_session.query(Submission).filter_by(id=sub_id).first()
    assert sub.status == "accepted"
    assert sub.verdict == "accepted"
