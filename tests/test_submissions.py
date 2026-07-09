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
