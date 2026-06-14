# Mini Code Judge

A backend code execution engine — submit C++ code, get verdicts (AC / WA / TLE / RE / CE).

Built with **Python + FastAPI + PostgreSQL + Redis + Docker**.

---

## Project structure

```
code-judge/
├── app/
│   ├── core/
│   │   ├── config.py       # All settings (DB URL, Redis URL, JWT secret)
│   │   ├── database.py     # SQLAlchemy engine + get_db() dependency
│   │   └── security.py     # Password hashing, JWT creation + verification
│   ├── models/
│   │   ├── user.py         # Users table
│   │   ├── problem.py      # Problems + TestCases tables
│   │   └── submission.py   # Submissions table (verdict stored here)
│   ├── schemas/
│   │   ├── user.py         # Pydantic request/response shapes
│   │   └── submission.py   # SubmissionCreate (in) + SubmissionOut (out)
│   ├── routers/
│   │   ├── auth.py         # POST /auth/register, POST /auth/login
│   │   ├── submissions.py  # POST /submissions, GET /submissions/{id}
│   │   └── problems.py     # GET /problems, POST /problems
│   ├── worker/
│   │   └── judge.py        # Compiles + runs code, writes verdict to DB
│   └── main.py             # FastAPI app, registers all routers
├── tests/
│   └── test_submissions.py
├── run_worker.py           # Start the RQ background worker
├── requirements.txt
└── .env.example
```

---

## How to run (Week 1 setup)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up PostgreSQL
```bash
# macOS
brew install postgresql && brew services start postgresql
createdb judge_db
createuser judge_user --pwprompt   # set password: judge_pass

# Ubuntu/Debian
sudo apt install postgresql
sudo -u postgres createdb judge_db
sudo -u postgres createuser judge_user --pwprompt
```

### 3. Set up Redis
```bash
# macOS
brew install redis && brew services start redis

# Ubuntu
sudo apt install redis-server && sudo service redis start
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env with your actual values
```

### 5. Start the API server
```bash
uvicorn app.main:app --reload
# Visit http://localhost:8000/docs for the interactive API explorer
```

### 6. Start the worker (separate terminal)
```bash
python run_worker.py
```

---

## API endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | /auth/register | No | Create account |
| POST | /auth/login | No | Get JWT token |
| GET | /problems | No | List problems |
| POST | /problems | Yes | Add a problem |
| POST | /problems/{id}/test-cases | Yes | Add test case |
| POST | /submissions | Yes | Submit code |
| GET | /submissions/{id} | Yes | Poll for verdict |
| GET | /submissions | Yes | My submissions |

---

## Verdict codes

| Code | Meaning |
|------|---------|
| `accepted` | All test cases passed |
| `wrong_answer` | Output didn't match expected |
| `time_limit_exceeded` | Exceeded 2 second limit |
| `runtime_error` | Program crashed (non-zero exit) |
| `compile_error` | g++ compilation failed |

---

## Submission lifecycle

```
Client POSTs code
       ↓
FastAPI saves to DB (status=pending)
       ↓
Job pushed to Redis queue
       ↓              ← Client polls GET /submissions/{id}
Worker picks up job
       ↓
Docker container: compile → run → compare output
       ↓
DB updated with verdict
       ↓
Client gets verdict on next poll
```
