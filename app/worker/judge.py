"""
The judge — compiles/runs submitted code and returns a verdict.

Supports:
  cpp:    compiled with g++, then executed
  python: syntax-checked with py_compile, then executed with python3
"""

import subprocess
import tempfile
import os
import time
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
    finally:
        db.close()


def _run_judge(submission_id: int, db: Session):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return

    submission.status = "running"
    db.commit()

    test_cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == submission.problem_id)
        .all()
    )
    if not test_cases:
        _set_verdict(db, submission, verdict="no_test_cases", status="error")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        run_command = _prepare_run_command(submission, tmpdir, db)
        if run_command is None:
            return  # compile/syntax error already recorded

        total_runtime_ms = 0.0

        for tc in test_cases:
            result = _run_test_case(run_command, tc.stdin)

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


def _prepare_run_command(submission: Submission, tmpdir: str, db: Session):
    """
    Writes the code to disk and compiles/checks it. Returns the command
    list to run it, or None (after recording a compile_error) on failure.
    """
    if submission.language == "python":
        src_path = os.path.join(tmpdir, "solution.py")
        with open(src_path, "w") as f:
            f.write(submission.code)

        check = subprocess.run(
            ["python3", "-m", "py_compile", src_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if check.returncode != 0:
            _set_verdict(
                db, submission,
                verdict="compile_error",
                status="compile_error",
                error_output=check.stderr[:5000],
            )
            return None

        return ["python3", src_path]

    # default: cpp
    src_path = os.path.join(tmpdir, "solution.cpp")
    exe_path = os.path.join(tmpdir, "solution")

    with open(src_path, "w") as f:
        f.write(submission.code)

    compile_result = subprocess.run(
        ["g++", "-O2", "-o", exe_path, src_path],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if compile_result.returncode != 0:
        _set_verdict(
            db, submission,
            verdict="compile_error",
            status="compile_error",
            error_output=compile_result.stderr[:5000],
        )
        return None

    return [exe_path]


def _run_test_case(run_command: list, stdin_data: str) -> dict:
    try:
        start = time.perf_counter()

        proc = subprocess.run(
            run_command,
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=settings.TIME_LIMIT_SECONDS,
        )

        elapsed_ms = (time.perf_counter() - start) * 1000

        if proc.returncode != 0:
            return {
                "verdict": "runtime_error",
                "stdout": proc.stdout,
                "stderr": proc.stderr[:2000],
                "runtime_ms": elapsed_ms,
            }

        return {
            "verdict": "accepted",
            "stdout": proc.stdout,
            "stderr": "",
            "runtime_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        return {"verdict": "time_limit_exceeded", "stdout": "", "stderr": "", "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000}


def _set_verdict(db: Session, submission: Submission, *, verdict: str, status: str,
                 runtime_ms: float = None, error_output: str = None):
    submission.verdict      = verdict
    submission.status       = status
    submission.runtime_ms   = runtime_ms
    submission.error_output = error_output
    submission.judged_at    = datetime.now(timezone.utc)
    db.commit()
