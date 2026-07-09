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


def _prepare_run_command(submission: Submission, tmpdir: str, db: Session):
    lang = submission.language

    if lang == "python":
        src = os.path.join(tmpdir, "solution.py")
        with open(src, "w") as f:
            f.write(submission.code)
        check = subprocess.run([
            "docker", "run", "--rm", "--net", "none",
            "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
            "mini-code-judge-sandbox:latest",
            "python3", "-m", "py_compile", "solution.py"
        ], capture_output=True, text=True, timeout=30)
        if check.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=check.stderr[:5000])
            return None
        return ["python3", "solution.py"]

    if lang == "c":
        src = os.path.join(tmpdir, "solution.c")
        with open(src, "w") as f:
            f.write(submission.code)
        result = subprocess.run([
            "docker", "run", "--rm", "--net", "none",
            "--memory", "512m",
            "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
            "mini-code-judge-sandbox:latest",
            "gcc", "-O2", "-o", "solution", "solution.c", "-lm"
        ], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=result.stderr[:5000])
            return None
        return ["./solution"]

    if lang == "java":
        src = os.path.join(tmpdir, "Main.java")
        with open(src, "w") as f:
            f.write(submission.code)
        result = subprocess.run([
            "docker", "run", "--rm", "--net", "none",
            "--memory", "512m",
            "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
            "mini-code-judge-sandbox:latest",
            "javac", "Main.java"
        ], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            _set_verdict(db, submission, verdict="compile_error",
                         status="compile_error", error_output=result.stderr[:5000])
            return None
        return ["java", f"-Xmx{settings.MEMORY_LIMIT_MB}m", "-cp", ".", "Main"]

    # default: cpp
    src = os.path.join(tmpdir, "solution.cpp")
    with open(src, "w") as f:
        f.write(submission.code)
    result = subprocess.run([
        "docker", "run", "--rm", "--net", "none",
        "--memory", "512m",
        "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
        "mini-code-judge-sandbox:latest",
        "g++", "-O2", "-o", "solution", "solution.cpp"
    ], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        _set_verdict(db, submission, verdict="compile_error",
                     status="compile_error", error_output=result.stderr[:5000])
        return None
    return ["./solution"]


def _run_test_case(run_command: list, stdin_data: str, tmpdir: str, submission_id: int) -> dict:
    mem_mb = settings.MEMORY_LIMIT_MB

    # Unique name for the container so we can kill it forcefully on timeout
    import uuid
    container_name = f"sandbox_{submission_id}_{uuid.uuid4().hex[:8]}"

    docker_run = [
        "docker", "run", "--rm", "-i",
        "--name", container_name,
        "--net", "none",
        "--memory", f"{mem_mb}m",
        "--memory-swap", f"{mem_mb}m",
        "--cpus", "1.0",
        "--pids-limit", "64",
        "--read-only",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=50m",
        "-v", f"{tmpdir}:/workspace:rw",
        "-w", "/workspace",
        "mini-code-judge-sandbox:latest"
    ] + run_command

    try:
        start = time.perf_counter()
        proc = subprocess.Popen(
            docker_run,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, stderr = proc.communicate(
                input=stdin_data.encode() if stdin_data else b"",
                timeout=settings.TIME_LIMIT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            # Kill the docker container by name
            subprocess.run(["docker", "kill", container_name], capture_output=True)
            proc.wait()
            return {
                "verdict": "time_limit_exceeded",
                "stdout": "", "stderr": "",
                "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000,
            }

        elapsed_ms = (time.perf_counter() - start) * 1000

        # Check for memory-related signals (SIGKILL from OOM or SIGSEGV)
        # Docker usually exits with 137 on OOM
        if proc.returncode in (-9, -11, 137):
            return {
                "verdict": "memory_limit_exceeded",
                "stdout": "", "stderr": "Process killed (memory limit or crash)",
                "runtime_ms": elapsed_ms,
            }

        if proc.returncode != 0:
            return {
                "verdict": "runtime_error",
                "stdout": stdout.decode(errors="replace"),
                "stderr": stderr.decode(errors="replace")[:2000],
                "runtime_ms": elapsed_ms,
            }

        return {
            "verdict": "accepted",
            "stdout": stdout.decode(errors="replace"),
            "stderr": "",
            "runtime_ms": elapsed_ms,
        }

    except MemoryError:
        return {"verdict": "memory_limit_exceeded", "stdout": "", "stderr": "", "runtime_ms": 0}
    except Exception as e:
        return {"verdict": "runtime_error", "stdout": "", "stderr": str(e)[:500], "runtime_ms": 0}



def _set_verdict(db: Session, submission: Submission, *, verdict: str, status: str,
                 runtime_ms: float = None, error_output: str = None):
    submission.verdict = verdict
    submission.status = status
    submission.runtime_ms = runtime_ms
    submission.error_output = error_output
    submission.judged_at = datetime.now(timezone.utc)
    db.commit()