"""
The judge — compiles/runs submitted code and returns a verdict.
Supports: cpp, c, java, python
"""
import subprocess
import tempfile
import os
import time
import traceback
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.submission import Submission
from app.models.problem import TestCase


def judge_submission(submission_id: int):
    db = SessionLocal()
    try:
        _run_judge(submission_id, db)
    except Exception:
        db.rollback()
        err_db = SessionLocal()
        try:
            submission = err_db.query(Submission).filter(Submission.id == submission_id).first()
            if submission and submission.status in ("pending", "running"):
                submission.status = "error"
                submission.verdict = "judge_error"
                submission.error_output = traceback.format_exc()[:5000]
                err_db.commit()
        except Exception:
            traceback.print_exc()
        finally:
            err_db.close()
    finally:
        db.close()


def _run_judge(submission_id: int, db: Session):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return

    # Check if this is a sample-only ("Run") request rather than a real submission
    sample_only = submission.is_sample_only

    submission.status = "running"
    db.commit()

    # Fetch test cases — sample_only = only is_sample=1, else all
    query = db.query(TestCase).filter(TestCase.problem_id == submission.problem_id)
    if sample_only:
        query = query.filter(TestCase.is_sample == 1)
    test_cases = query.all()

    if not test_cases:
        msg = "No sample test cases found" if sample_only else "No test cases found"
        _set_verdict(db, submission, verdict="no_test_cases", status="error", error_output=msg)
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        run_command = _prepare_run_command(submission, tmpdir, db)
        if run_command is None:
            return  # compile error already recorded

        total_runtime_ms = 0.0

        for tc in test_cases:
            result = _run_test_case(run_command, tc.stdin, tmpdir, submission.id)

            if result["verdict"] != "accepted":
                _set_verdict(
                    db, submission,
                    verdict=result["verdict"],
                    status=result["verdict"],
                    runtime_ms=result["runtime_ms"],
                    error_output=result.get("stderr", ""),
                )
                return

            total_runtime_ms = max(total_runtime_ms, result["runtime_ms"])
            actual = result["stdout"].strip()
            expected = tc.expected.strip()

            if actual != expected:
                _set_verdict(
                    db, submission,
                    verdict="wrong_answer",
                    status="wrong_answer",
                    runtime_ms=total_runtime_ms,
                )
                return

        _set_verdict(
            db, submission,
            verdict="accepted",
            status="accepted",
            runtime_ms=total_runtime_ms,
        )


import shutil
from app.worker.sandbox import LocalSandbox, DockerSandbox

def _get_sandbox() -> 'Sandbox':
    if shutil.which("docker"):
        return DockerSandbox()
    return LocalSandbox()

def _prepare_run_command(submission: Submission, tmpdir: str, db: Session):
    sandbox = _get_sandbox()
    result = sandbox.compile(submission.language, submission.code, tmpdir)
    if not result["success"]:
        _set_verdict(db, submission, verdict="compile_error",
                     status="compile_error", error_output=result["error_output"])
        return None
    return result["run_command"]

def _run_test_case(run_command: list, stdin_data: str, tmpdir: str, submission_id: int):
    sandbox = _get_sandbox()
    return sandbox.run(run_command, stdin_data, tmpdir, submission_id)




def _set_verdict(db: Session, submission: Submission, *, verdict: str, status: str,
                 runtime_ms: float = None, error_output: str = None):
    submission.verdict = verdict
    submission.status = status
    submission.runtime_ms = runtime_ms
    submission.error_output = error_output
    submission.judged_at = datetime.now(timezone.utc)
    db.commit()