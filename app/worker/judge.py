"""
The judge — runs inside a Docker container, returns a verdict.

This module is called by the RQ worker (not by FastAPI directly).
It does the actual work:
  1. Write the code to a temp file
  2. Compile it
  3. Run it against each test case
  4. Compare output → verdict
  5. Update the DB row

Why subprocess?
  Python's subprocess module lets us run shell commands (g++, ./a.out)
  and capture their output, exit codes, and timing — exactly what a judge needs.
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
    """
    Entry point called by the RQ worker.
    Creates its own DB session (workers are separate processes from FastAPI).
    """
    db = SessionLocal()
    try:
        _run_judge(submission_id, db)
    finally:
        db.close()


def _run_judge(submission_id: int, db: Session):
    # ── 1. Fetch submission from DB ──────────────────────────────────────────
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        return  # Shouldn't happen, but guard anyway

    # Mark as running so the client knows we started
    submission.status = "running"
    db.commit()

    # ── 2. Fetch all test cases for this problem ─────────────────────────────
    test_cases = (
        db.query(TestCase)
        .filter(TestCase.problem_id == submission.problem_id)
        .all()
    )
    if not test_cases:
        _set_verdict(db, submission, verdict="no_test_cases", status="error")
        return

    # ── 3. Write code to a temp file and compile ─────────────────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "solution.cpp")
        exe_path = os.path.join(tmpdir, "solution")

        with open(src_path, "w") as f:
            f.write(submission.code)

        compile_result = subprocess.run(
            ["g++", "-O2", "-o", exe_path, src_path],
            capture_output=True,
            text=True,
            timeout=30,   # Compilation shouldn't take more than 30s
        )

        # Compilation error — stop here, show stderr to user
        if compile_result.returncode != 0:
            _set_verdict(
                db, submission,
                verdict="compile_error",
                status="compile_error",
                error_output=compile_result.stderr[:5000],  # Truncate huge errors
            )
            return

        # ── 4. Run against each test case ────────────────────────────────────
        total_runtime_ms = 0.0
        peak_memory_kb = 0

        for tc in test_cases:
            result = _run_test_case(exe_path, tc.stdin)

            if result["verdict"] != "accepted":
                # Fail fast — stop at first failing test case
                _set_verdict(
                    db, submission,
                    verdict=result["verdict"],
                    status=result["verdict"],
                    runtime_ms=result["runtime_ms"],
                    error_output=result.get("stderr", ""),
                )
                return

            total_runtime_ms = max(total_runtime_ms, result["runtime_ms"])

            # Compare actual output vs expected (strip trailing whitespace/newlines)
            actual   = result["stdout"].strip()
            expected = tc.expected.strip()

            if actual != expected:
                _set_verdict(
                    db, submission,
                    verdict="wrong_answer",
                    status="wrong_answer",
                    runtime_ms=total_runtime_ms,
                )
                return

        # ── 5. All test cases passed! ─────────────────────────────────────────
        _set_verdict(
            db, submission,
            verdict="accepted",
            status="accepted",
            runtime_ms=total_runtime_ms,
        )


def _run_test_case(exe_path: str, stdin_data: str) -> dict:
    """
    Run the compiled binary against one test case.
    Returns a dict with verdict, stdout, stderr, and runtime_ms.

    In Week 8, you'll replace this subprocess call with a Docker run command:
        docker run --rm --memory=256m --cpus=0.5 ...
    The interface stays the same — only the execution layer changes.
    """
    try:
        start = time.perf_counter()

        proc = subprocess.run(
            [exe_path],
            input=stdin_data,
            capture_output=True,
            text=True,
            timeout=settings.TIME_LIMIT_SECONDS,  # Kills the process if too slow
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
            "verdict": "accepted",  # Means "ran successfully" — output checked separately
            "stdout": proc.stdout,
            "stderr": "",
            "runtime_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        return {"verdict": "time_limit_exceeded", "stdout": "", "stderr": "", "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000}


def _set_verdict(db: Session, submission: Submission, *, verdict: str, status: str,
                 runtime_ms: float = None, error_output: str = None):
    """Helper to update the submission row and commit."""
    submission.verdict      = verdict
    submission.status       = status
    submission.runtime_ms   = runtime_ms
    submission.error_output = error_output
    submission.judged_at    = datetime.now(timezone.utc)
    db.commit()
