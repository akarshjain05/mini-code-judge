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
                                          v  spawns
                              Background thread: compiles + runs
                              submitted code against test cases
                              with OS resource limits (rlimit)
```

The backend is a single FastAPI service. Submitted code is compiled/interpreted (`gcc`/`g++`/`javac`/`python3`) and run as a subprocess with OS-level resource limits (CPU time via a hard timeout, memory via `RLIMIT_AS`/`-Xmx`, output size, open files, and process count), each run in its own process group so a timeout or runaway process can be killed cleanly without leaking children.

## Engineering decisions worth knowing

**Judging happens in a background thread inside the web process, not a separate queue worker.** `render.yaml` still provisions a second RQ (Redis Queue) worker service — that was the original design, and the code to support it (`run_worker.py`) is still in the repo. In practice, submissions are judged with a plain background `threading.Thread` spawned directly from the request handler (see `app/routers/submissions.py`); nothing actually enqueues jobs onto the Redis queue the worker service listens on, so that worker service currently runs idle. This was a deliberate simplification to get judging working reliably within Render's free tier, but it's a known inconsistency that hasn't been cleaned up yet — the honest fix is either wiring submissions back through RQ properly, or removing the now-unused worker service from `render.yaml`. Noting it here rather than letting the architecture diagram imply more than it does.

**Why this matters in practice:** background threads inside a single web process work fine at low concurrency, but they don't survive a process restart/redeploy (an in-flight submission would just be lost, stuck at "pending"), and they don't scale across multiple web processes if `WEB_CONCURRENCY` is ever raised. A real queue (RQ, properly wired this time, or Celery) is the correct fix if this needed to handle real concurrent load.

**Code execution security is intentionally scoped down, not solved.** Untrusted code runs directly on the host inside the FastAPI worker process's environment — there's no container, gVisor, or firejail sandbox per submission. What *is* in place: per-run CPU timeout, memory cap, output-size cap, open-file cap, and a process-count cap (specifically to stop fork bombs — `while(1) fork();` is contained rather than taking the whole judge down). What's *not* in place: network isolation (submitted code can still make outbound network calls) and filesystem isolation beyond a temp directory. For a production judge handling untrusted code at scale, the right fix is running each submission in a locked-down container (gVisor or Firecracker, the way Judge0 and most real online judges do it) with no network namespace. Skipped here because it's expensive/awkward to run reliably on Render's free tier, not because it wasn't considered.

**Java needs a different memory-limiting strategy than the other languages.** The JVM reserves large virtual address space up front (code cache, metaspace, thread stacks) regardless of actual heap usage, so capping it with the OS-level `RLIMIT_AS` (which the other three languages use directly) kills the JVM before it runs any user code at all. Java's memory is capped with `-Xmx` on the `java` command instead, while `RLIMIT_AS` is skipped specifically for that language.

## Tech stack

**Backend:** FastAPI, SQLAlchemy, PostgreSQL, Pydantic, JWT auth (`python-jose`), `slowapi` for rate limiting, Gemini API for AI review.
**Frontend:** Vanilla HTML/CSS/JS (no framework/build step) — deliberately simple, hash-based routing, `fetch`-based API calls.
**Judge:** subprocess-based compilation/execution with OS resource limits (see above).
**Deployment:** Render (web service + Postgres + Redis), frontend on Render/Netlify.

## Running locally

```bash
git clone https://github.com/akarshjain05/mini-code-judge.git
cd mini-code-judge
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env — at minimum set DATABASE_URL to a local Postgres instance
# and generate a real SECRET_KEY:
#   python3 -c "import secrets; print(secrets.token_hex(32))"

uvicorn app.main:app --reload
```

The frontend is static — open `index.html` directly, or serve it with any static file server, pointing `API_URL` in your `.env`/config at your local backend.

You'll need `gcc`, `g++`, and a JDK (`javac`/`java`) on your machine (or in whatever environment you run the backend in) for C/C++/Java submissions to compile and run. You'll also need Redis running locally for login/logout and email verification to work (JWT blacklist and login-attempt tracking live there) — the rest of the app runs fine without it.

## Known limitations

Being upfront about what's out of scope right now, rather than leaving it to be discovered:

- **No real sandboxing for untrusted code** (see above) — resource limits only, no container/network isolation.
- **Judging isn't durable** — an in-flight submission is lost if the web process restarts mid-judge (background thread, not a persisted queue job).
- **Test coverage is thin** relative to the project's surface area — solid coverage on the submission flow, little to none on auth, contests, leaderboard, or the AI review path.
- **No CI pipeline** — tests exist but aren't run automatically on push yet.
- **RQ worker service in `render.yaml` is currently dead weight** (see above) — either wire it up properly or remove it.

## License

MIT
