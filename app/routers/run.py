"""
/run endpoint — runs code against sample test cases only.
NOT saved as a submission. Does NOT count toward history.
Returns immediate result with which test case failed and why.
"""
import subprocess
import tempfile
import os
import time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.models.problem import Problem, TestCase

router = APIRouter(tags=["run"])


class RunRequest(BaseModel):
    problem_id: int
    language: str
    code: str


@router.post("/run")
def run_code(
    payload: RunRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # Only sample test cases
    sample_tests = db.query(TestCase).filter(
        TestCase.problem_id == payload.problem_id,
        TestCase.is_sample == 1
    ).all()

    if not sample_tests:
        raise HTTPException(status_code=400, detail="No sample test cases available for this problem")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Compile / prepare
        run_cmd, compile_error = _prepare(payload.language, payload.code, tmpdir)
        if compile_error:
            return {"verdict": "compile_error", "error": compile_error}

        # Run against each sample test
        total_runtime = 0.0
        for i, tc in enumerate(sample_tests, 1):
            result = _run_one(run_cmd, tc.stdin)
            total_runtime = max(total_runtime, result["runtime_ms"])

            if result["verdict"] == "time_limit_exceeded":
                return {
                    "verdict": "time_limit_exceeded",
                    "failed_case": i,
                    "input": tc.stdin,
                    "runtime_ms": result["runtime_ms"],
                }

            if result["verdict"] == "runtime_error":
                return {
                    "verdict": "runtime_error",
                    "failed_case": i,
                    "input": tc.stdin,
                    "error": result["stderr"],
                    "runtime_ms": result["runtime_ms"],
                }

            actual = result["stdout"].strip()
            expected = tc.expected.strip()
            if actual != expected:
                return {
                    "verdict": "wrong_answer",
                    "failed_case": i,
                    "input": tc.stdin,
                    "expected": expected,
                    "actual": actual,
                    "runtime_ms": result["runtime_ms"],
                }

        return {
            "verdict": "accepted",
            "passed": len(sample_tests),
            "total": len(sample_tests),
            "runtime_ms": total_runtime,
        }


def _prepare(language: str, code: str, tmpdir: str):
    """Compile/prepare code. Returns (run_command, error_string)."""
    if language == "python":
        src = os.path.join(tmpdir, "solution.py")
        with open(src, "w") as f:
            f.write(code)
        check = subprocess.run(["python3", "-m", "py_compile", src],
                               capture_output=True, text=True, timeout=10)
        if check.returncode != 0:
            return None, check.stderr[:3000]
        return ["python3", src], None

    if language == "c":
        src = os.path.join(tmpdir, "solution.c")
        exe = os.path.join(tmpdir, "solution")
        with open(src, "w") as f:
            f.write(code)
        r = subprocess.run(["gcc", "-O2", "-o", exe, src, "-lm"],
                           capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None, r.stderr[:3000]
        return [exe], None

    if language == "java":
        src = os.path.join(tmpdir, "Main.java")
        with open(src, "w") as f:
            f.write(code)
        r = subprocess.run(["javac", src], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            return None, r.stderr[:3000]
        return ["java", "-cp", tmpdir, "Main"], None

    # Default: cpp
    src = os.path.join(tmpdir, "solution.cpp")
    exe = os.path.join(tmpdir, "solution")
    with open(src, "w") as f:
        f.write(code)
    r = subprocess.run(["g++", "-O2", "-o", exe, src],
                       capture_output=True, text=True, timeout=15)
    if r.returncode != 0:
        return None, r.stderr[:3000]
    return [exe], None


def _run_one(cmd, stdin_data: str) -> dict:
    try:
        start = time.perf_counter()
        proc = subprocess.run(cmd, input=stdin_data, capture_output=True,
                              text=True, timeout=settings.TIME_LIMIT_SECONDS)
        elapsed = (time.perf_counter() - start) * 1000
        if proc.returncode != 0:
            return {"verdict": "runtime_error", "stdout": "", "stderr": proc.stderr[:1000], "runtime_ms": elapsed}
        return {"verdict": "accepted", "stdout": proc.stdout, "stderr": "", "runtime_ms": elapsed}
    except subprocess.TimeoutExpired:
        return {"verdict": "time_limit_exceeded", "stdout": "", "stderr": "", "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000}
