import pytest
from unittest.mock import patch, MagicMock
import subprocess
from app.models.problem import Problem, TestCase
from app.models.submission import Submission
from app.worker.judge import judge_submission
import app.core.database
from tests.conftest import TestingSession
from app.models.user import User

def setup_submission(db_session, lang, code):
    u = db_session.query(User).filter_by(username="testuser").first()
    if not u:
        u = User(username="testuser", email="test@test.com", password="pw", is_verified=True)
        db_session.add(u)
        db_session.commit()

    p = Problem(title="Test", description="Test", difficulty="EASY")
    db_session.add(p)
    db_session.commit()
    
    tc = TestCase(problem_id=p.id, stdin="1 2\n", expected="3\n", is_sample=False)
    db_session.add(tc)
    
    sub = Submission(user_id=u.id, problem_id=p.id, language=lang, code=code)
    db_session.add(sub)
    db_session.commit()
    return sub.id

def mock_judge_env(sub_id, run_mock, popen_mock):
    with patch("app.worker.judge.SessionLocal", TestingSession):
        with patch("app.worker.judge.shutil.which", return_value="/usr/bin/docker"):
            with patch("app.worker.judge.subprocess.run", run_mock):
                with patch("app.worker.judge.subprocess.Popen", popen_mock):
                    judge_submission(sub_id)


@pytest.mark.parametrize("lang", ["c", "cpp", "java", "python"])
def test_docker_compile_error(db_session, lang):
    sub_id = setup_submission(db_session, lang, "bad code")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 1
    run_mock.return_value.stderr = "compile error"
    
    popen_mock = MagicMock()
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "compile_error"
    assert "compile error" in sub.error_output
    
    # Assert run was called with docker for compile
    assert "docker" in run_mock.call_args[0][0]


@pytest.mark.parametrize("lang", ["c", "cpp", "java", "python"])
def test_docker_accepted(db_session, lang):
    sub_id = setup_submission(db_session, lang, "good code")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 0
    
    popen_mock = MagicMock()
    popen_mock.return_value.communicate.return_value = (b"3\n", b"")
    popen_mock.return_value.returncode = 0
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "accepted"


def test_docker_wrong_answer(db_session):
    sub_id = setup_submission(db_session, "python", "wrong code")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 0
    
    popen_mock = MagicMock()
    popen_mock.return_value.communicate.return_value = (b"4\n", b"")
    popen_mock.return_value.returncode = 0
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "wrong_answer"


def test_docker_time_limit_exceeded(db_session):
    sub_id = setup_submission(db_session, "python", "while True: pass")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 0
    
    popen_mock = MagicMock()
    popen_mock.return_value.communicate.side_effect = subprocess.TimeoutExpired(cmd="docker", timeout=2)
    popen_mock.return_value.returncode = None
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "time_limit_exceeded"


def test_docker_runtime_error(db_session):
    sub_id = setup_submission(db_session, "python", "1/0")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 0
    
    popen_mock = MagicMock()
    popen_mock.return_value.communicate.return_value = (b"", b"ZeroDivisionError")
    popen_mock.return_value.returncode = 1
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "runtime_error"
    assert "ZeroDivisionError" in sub.error_output


def test_docker_memory_limit_exceeded(db_session):
    sub_id = setup_submission(db_session, "python", "a = [1] * 10**9")
    
    run_mock = MagicMock()
    run_mock.return_value.returncode = 0
    
    popen_mock = MagicMock()
    popen_mock.return_value.communicate.return_value = (b"", b"")
    popen_mock.return_value.returncode = 137 # Docker OOM exit code
    
    mock_judge_env(sub_id, run_mock, popen_mock)
    
    db_session.expire_all()
    sub = db_session.query(Submission).get(sub_id)
    
    assert sub.verdict == "memory_limit_exceeded"
