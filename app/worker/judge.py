"""
The judge — compiles/runs submitted code and returns a verdict.
Supports: cpp, c, java, python
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

    # Check if this is a sample-only run
    sample_only = submission.error_output == "SAMPLE_ONLY"

    submission.status = "running"
    if sample_only:
        submission.error_output = None  # clear the flag
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
    lang = submission.language

    if lang == "python":
        src = os.path.join(tmpdir, "solution.py")
        with open(src, "w") as f:
            f.write(submission.code)
        check = subprocess.run(["python3", "-m", "py_compile", src],
                               capture_output=True, text=True, timeout=30)
        if check.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=check.stderr[:5000])
            return None
        return ["python3", src]

    if lang == "c":
        src = os.path.join(tmpdir, "solution.c")
        exe = os.path.join(tmpdir, "solution")
        with open(src, "w") as f:
            f.write(submission.code)
        result = subprocess.run(["gcc", "-O2", "-o", exe, src, "-lm"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=result.stderr[:5000])
            return None
        return [exe]

    if lang == "java":
        src = os.path.join(tmpdir, "Main.java")
        with open(src, "w") as f:
            f.write(submission.code)
        result = subprocess.run(["javac", src], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=result.stderr[:5000])
            return None
        return ["java", "-cp", tmpdir, "Main"]

    # default: cpp
    src = os.path.join(tmpdir, "solution.cpp")
    exe = os.path.join(tmpdir, "solution")
    with open(src, "w") as f:
        f.write(submission.code)
    result = subprocess.run(["g++", "-O2", "-o", exe, src],
                            capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        _set_verdict(db, submission, verdict="compile_error",
                     status="compile_error", error_output=result.stderr[:5000])
        return None
    return [exe]


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
            return {"verdict": "runtime_error", "stdout": proc.stdout,
                    "stderr": proc.stderr[:2000], "runtime_ms": elapsed_ms}
        return {"verdict": "accepted", "stdout": proc.stdout, "stderr": "", "runtime_ms": elapsed_ms}
    except subprocess.TimeoutExpired:
        return {"verdict": "time_limit_exceeded", "stdout": "", "stderr": "",
                "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000}


def _set_verdict(db: Session, submission: Submission, *, verdict: str, status: str,
                 runtime_ms: float = None, error_output: str = None):
    submission.verdict = verdict
    submission.status = status
    submission.runtime_ms = runtime_ms
    submission.error_output = error_output
    submission.judged_at = datetime.now(timezone.utc)
    db.commit()