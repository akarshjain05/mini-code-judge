import os
import time
import uuid
import signal
import subprocess
from typing import Optional, Dict, List
from app.core.config import settings

class Sandbox:
    """Base interface for executing untrusted code."""
    
    def compile(self, language: str, code: str, tmpdir: str) -> dict:
        """
        Compiles the code. Returns a dictionary with:
        - success (bool)
        - run_command (list or None)
        - error_output (str)
        """
        raise NotImplementedError

    def run(self, run_command: List[str], stdin_data: str, tmpdir: str, submission_id: int) -> dict:
        """
        Runs the compiled code against a single test case. Returns a dictionary with:
        - verdict (str)
        - stdout (str)
        - stderr (str)
        - runtime_ms (float)
        """
        raise NotImplementedError


class LocalSandbox(Sandbox):
    def compile(self, language: str, code: str, tmpdir: str) -> dict:
        if language == "python":
            src = os.path.join(tmpdir, "solution.py")
            with open(src, "w") as f:
                f.write(code)
            check = subprocess.run(["python3", "-m", "py_compile", src],
                                   capture_output=True, text=True, timeout=30)
            if check.returncode != 0:
                return {"success": False, "error_output": check.stderr[:5000]}
            return {"success": True, "run_command": ["python3", src]}

        if language == "c":
            src = os.path.join(tmpdir, "solution.c")
            exe = os.path.join(tmpdir, "solution")
            with open(src, "w") as f:
                f.write(code)
            result = subprocess.run(["gcc", "-O2", "-o", exe, src, "-lm"],
                                    capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"success": False, "error_output": result.stderr[:5000]}
            return {"success": True, "run_command": [exe]}

        if language == "java":
            src = os.path.join(tmpdir, "Main.java")
            with open(src, "w") as f:
                f.write(code)
            result = subprocess.run(["javac", src], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"success": False, "error_output": result.stderr[:5000]}
            return {"success": True, "run_command": ["java", f"-Xmx{settings.MEMORY_LIMIT_MB}m", "-cp", tmpdir, "Main"]}

        # default: cpp
        src = os.path.join(tmpdir, "solution.cpp")
        exe = os.path.join(tmpdir, "solution")
        with open(src, "w") as f:
            f.write(code)
        result = subprocess.run(["g++", "-O2", "-o", exe, src],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"success": False, "error_output": result.stderr[:5000]}
        return {"success": True, "run_command": [exe]}

    def run(self, run_command: List[str], stdin_data: str, tmpdir: str, submission_id: int) -> dict:
        import resource
        mem_bytes = settings.MEMORY_LIMIT_MB * 1024 * 1024
        is_java = run_command and run_command[0] == "java"

        def _preexec():
            if not is_java:
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
            resource.setrlimit(resource.RLIMIT_NPROC, (512, 512))
            os.setsid()

        safe_env = {
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LANG": "en_US.UTF-8",
        }

        try:
            start = time.perf_counter()
            proc = subprocess.Popen(
                run_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=safe_env,
                preexec_fn=_preexec,
            )
            try:
                stdout, stderr = proc.communicate(
                    input=stdin_data.encode() if stdin_data else b"",
                    timeout=settings.TIME_LIMIT_SECONDS,
                )
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except ProcessLookupError:
                    proc.kill()
                proc.wait()
                return {
                    "verdict": "time_limit_exceeded",
                    "stdout": "", "stderr": "",
                    "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000,
                }

            elapsed_ms = (time.perf_counter() - start) * 1000

            if proc.returncode in (-9, -11):
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


class DockerSandbox(Sandbox):
    def compile(self, language: str, code: str, tmpdir: str) -> dict:
        if language == "python":
            src = os.path.join(tmpdir, "solution.py")
            with open(src, "w") as f:
                f.write(code)
            check = subprocess.run([
                "docker", "run", "--rm", "--net", "none",
                "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
                "mini-code-judge-sandbox:latest",
                "python3", "-m", "py_compile", "solution.py"
            ], capture_output=True, text=True, timeout=30)
            if check.returncode != 0:
                return {"success": False, "error_output": check.stderr[:5000]}
            return {"success": True, "run_command": ["python3", "solution.py"]}

        if language == "c":
            src = os.path.join(tmpdir, "solution.c")
            with open(src, "w") as f:
                f.write(code)
            result = subprocess.run([
                "docker", "run", "--rm", "--net", "none",
                "--memory", "512m",
                "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
                "mini-code-judge-sandbox:latest",
                "gcc", "-O2", "-o", "solution", "solution.c", "-lm"
            ], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"success": False, "error_output": result.stderr[:5000]}
            return {"success": True, "run_command": ["./solution"]}

        if language == "java":
            src = os.path.join(tmpdir, "Main.java")
            with open(src, "w") as f:
                f.write(code)
            result = subprocess.run([
                "docker", "run", "--rm", "--net", "none",
                "--memory", "512m",
                "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
                "mini-code-judge-sandbox:latest",
                "javac", "Main.java"
            ], capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return {"success": False, "error_output": result.stderr[:5000]}
            return {"success": True, "run_command": ["java", f"-Xmx{settings.MEMORY_LIMIT_MB}m", "-cp", ".", "Main"]}

        # default: cpp
        src = os.path.join(tmpdir, "solution.cpp")
        with open(src, "w") as f:
            f.write(code)
        result = subprocess.run([
            "docker", "run", "--rm", "--net", "none",
            "--memory", "512m",
            "-v", f"{tmpdir}:/workspace", "-w", "/workspace",
            "mini-code-judge-sandbox:latest",
            "g++", "-O2", "-o", "solution", "solution.cpp"
        ], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"success": False, "error_output": result.stderr[:5000]}
        return {"success": True, "run_command": ["./solution"]}

    def run(self, run_command: List[str], stdin_data: str, tmpdir: str, submission_id: int) -> dict:
        mem_mb = settings.MEMORY_LIMIT_MB
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
                subprocess.run(["docker", "kill", container_name], capture_output=True)
                proc.wait()
                return {
                    "verdict": "time_limit_exceeded",
                    "stdout": "", "stderr": "",
                    "runtime_ms": settings.TIME_LIMIT_SECONDS * 1000,
                }

            elapsed_ms = (time.perf_counter() - start) * 1000

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
