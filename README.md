# Mini Code Judge

A full-stack competitive programming judge — write code in the browser, run it against sample cases, submit for full judging against hidden test cases, and track your progress across problems, contests, and a leaderboard. Built from scratch to learn how systems like Codeforces/LeetCode actually work under the hood: compiling and running untrusted code safely, judging correctness, and building the surrounding product around that core.

Live: [mini-code-judge-frontend.onrender.com](https://mini-code-judge-frontend.onrender.com)

## What it does

- **Problems & judging** — write C, C++, Java, or Python in-browser, `Run` against visible sample cases for quick feedback, `Submit` to judge against the full hidden test suite. Verdicts: Accepted, Wrong Answer, Time Limit Exceeded, Memory Limit Exceeded, Runtime Error, Compile Error.
- **Auth** — email/password with verification, Google Sign-In, GitHub OAuth, password reset, account lockout after repeated failed logins.
- **Contests** — timed contests with a live leaderboard, per-problem scoring, and penalty tracking for wrong attempts.
- **Leaderboard & analytics** — global rankings, acceptance-rate breakdowns per problem, per-user submission history with language/verdict filters.
- **AI Code Review** — after a submission, get an LLM-generated review (complexity analysis, what went wrong, suggested improvements) powered by Gemini.
- **Admin dashboard** — problem/test-case management, submission oversight, contest creation.

## Architecture

```
 Frontend (vanilla JS/HTML)  --REST-->  FastAPI (Render)  --ORM-->  PostgreSQL
                                          |  auth, problems, submissions,
                                          |  judge trigger, contests,
                                          |  leaderboard, admin
                                          |
                                          | enqueue (Redis)
                                          v 
                              RQ Worker (AWS EC2 / Ubuntu)
                                          |
                                          v  docker run
                              Isolated Docker Sandbox (per test case)
                              (No Network, Memory Capped, Read-Only FS)
```

The backend is a FastAPI service that enqueues judging jobs onto a Redis queue using `RQ`. A dedicated background worker process (ideally hosted on an external Docker-capable server like AWS EC2) pulls these jobs and judges them. 

Submitted code is compiled (`gcc`/`g++`/`javac`/`python3`) and run inside highly secure, ephemeral **Docker containers**.

## Engineering decisions worth knowing

**Enterprise-Grade Docker Sandboxing.** Code execution security is taken very seriously. Untrusted code is completely isolated using Docker. Every compilation step and test-case execution runs inside a fresh container with strict boundaries:
- `--net none`: Prevents all outbound internet access so malicious code cannot ping external servers or exfiltrate data.
- `--memory` and `--memory-swap`: Hard caps RAM usage (e.g. 256MB/512MB) to prevent OOM attacks.
- `--cpus 1.0`: Limits processing power.
- `--pids-limit 64`: Strictly limits the number of processes to defend against fork bombs (`while(1) fork();`).
- `--read-only` & `--tmpfs`: The filesystem is locked down. The code cannot modify the container, with only a small temporary RAM disk available for runtimes (like Java) that require temp files.

**Auto-Fallback Judging Engine.** If you decide to run the worker process on a server that does *not* have Docker installed (like Render's free Python environment), the judging engine automatically detects this and gracefully falls back to a local OS-level sandbox. This local sandbox uses Python's Unix `resource` library (`RLIMIT_AS`, `RLIMIT_NPROC`, `RLIMIT_FSIZE`) to provide best-effort local security.

**Distributed Queue System.** Submissions are processed durably via `RQ` (Redis Queue). The web process immediately accepts the submission and places it on the queue. If the web server crashes or restarts, the submission is not lost. The worker process scales horizontally; you can spin up as many AWS EC2 workers as you want, and they will all pull from the same Redis queue to process submissions in parallel.

## Tech stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL, Pydantic, JWT auth (`python-jose`), `slowapi` for rate limiting, Gemini API for AI review, `rq` (Redis Queue) for asynchronous worker tasks.
**Worker Sandbox:** Docker, Alpine/Debian base images, Bash.
**Frontend:** Vanilla HTML/CSS/JS (no framework/build step) — deliberately simple, hash-based routing, `fetch`-based API calls.
**Deployment:** 
- Web Server + DB + Redis: Render
- Worker Server: AWS EC2 / DigitalOcean (Recommended for Docker Support)

## Running locally

```bash
git clone https://github.com/akarshjain05/mini-code-judge.git
cd mini-code-judge
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set DATABASE_URL to a local Postgres instance,
# provide REDIS_URL, and generate a real SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_hex(32))"

# Start the web server
uvicorn app.main:app --reload

# In a separate terminal window, start the worker
python3 run_worker.py
```

The frontend is static — open `index.html` directly, or serve it with any static file server, pointing `API_URL` in your `.env`/config at your local backend.

You'll need `docker` running on your local machine for the primary sandbox to work. If Docker is not found, the app requires `gcc`, `g++`, and a JDK (`javac`/`java`) natively installed to use the local OS-level fallback sandbox. 

## Known limitations

Being upfront about what's out of scope right now:
- **Test coverage is thin** relative to the project's surface area — solid coverage on the submission flow, little to none on auth, contests, leaderboard, or the AI review path.
- **No CI pipeline** — tests exist but aren't run automatically on push yet.

## License

MIT
