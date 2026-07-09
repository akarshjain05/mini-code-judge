import re

with open("judge_old.py") as f:
    old_code = f.read()

with open("app/worker/judge.py") as f:
    new_code = f.read()

# Extract old functions
old_prep_match = re.search(r'(def _prepare_run_command\(.*?return \[exe\]\n)', old_code, re.DOTALL)
old_prep = old_prep_match.group(1).replace("def _prepare_run_command", "def _prepare_run_command_local")

old_run_match = re.search(r'(def _run_test_case\(run_command: list, stdin_data: str\) -> dict:.*?return \{"verdict": "runtime_error", "stdout": "", "stderr": str\(e\)\[:500\], "runtime_ms": 0\}\n)', old_code, re.DOTALL)
old_run = old_run_match.group(1).replace("def _run_test_case", "def _run_test_case_local")

# Extract new functions
new_prep_match = re.search(r'(def _prepare_run_command\(.*?return \["\./solution"\]\n)', new_code, re.DOTALL)
new_prep = new_prep_match.group(1).replace("def _prepare_run_command", "def _prepare_run_command_docker")

new_run_match = re.search(r'(def _run_test_case\(run_command: list, stdin_data: str, tmpdir: str, submission_id: int\) -> dict:.*?return \{"verdict": "runtime_error", "stdout": "", "stderr": str\(e\)\[:500\], "runtime_ms": 0\}\n)', new_code, re.DOTALL)
new_run = new_run_match.group(1).replace("def _run_test_case", "def _run_test_case_docker")

# Replace in new_code
header = new_code[:new_prep_match.start()]
footer = new_code[new_run_match.end():]

router_code = """
import shutil

def _prepare_run_command(submission, tmpdir, db):
    if shutil.which("docker"):
        return _prepare_run_command_docker(submission, tmpdir, db)
    return _prepare_run_command_local(submission, tmpdir, db)

def _run_test_case(run_command, stdin_data, tmpdir, submission_id):
    if shutil.which("docker"):
        return _run_test_case_docker(run_command, stdin_data, tmpdir, submission_id)
    # The local version doesn't take tmpdir or submission_id
    return _run_test_case_local(run_command, stdin_data)

"""

final_code = header + old_prep + "\n\n" + old_run + "\n\n" + new_prep + "\n\n" + new_run + "\n\n" + router_code + footer

# We need to add `import shutil` at the top if not present, but router_code has it
# Actually just putting it in router_code works fine.

with open("app/worker/judge.py", "w") as f:
    f.write(final_code)
