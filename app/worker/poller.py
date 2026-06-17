"""
In-process background worker.

Runs inside the SAME process as the FastAPI app, so we don't need a
separate paid worker service on Render. A background thread polls the
database every few seconds for submissions with status="pending" and
judges them using the existing judge.py logic.
"""

import threading
import time
import traceback

from app.core.database import SessionLocal
from app.models.submission import Submission
from app.worker.judge import _run_judge

POLL_INTERVAL_SECONDS = 2


def _poll_loop():
    while True:
        db = SessionLocal()
        try:
            pending = (
                db.query(Submission)
                .filter(Submission.status == "pending")
                .all()
            )
            for sub in pending:
                try:
                    _run_judge(sub.id, db)
                except Exception:
                    sub.status = "error"
                    sub.error_output = traceback.format_exc()[:5000]
                    db.commit()
        except Exception:
            traceback.print_exc()
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


def start_background_worker():
    """Call once at FastAPI startup to begin polling for pending submissions."""
    thread = threading.Thread(target=_poll_loop, daemon=True, name="judge-poller")
    thread.start()
EOFcd files
mkdir -p app/worker

cat > app/worker/poller.py << 'EOF'
"""
In-process background worker.

Runs inside the SAME process as the FastAPI app, so we don't need a
separate paid worker service on Render. A background thread polls the
database every few seconds for submissions with status="pending" and
judges them using the existing judge.py logic.
"""

import threading
import time
import traceback

from app.core.database import SessionLocal
from app.models.submission import Submission
from app.worker.judge import _run_judge

POLL_INTERVAL_SECONDS = 2


def _poll_loop():
    while True:
        db = SessionLocal()
        try:
            pending = (
                db.query(Submission)
                .filter(Submission.status == "pending")
                .all()
            )
            for sub in pending:
                try:
                    _run_judge(sub.id, db)
                except Exception:
                    sub.status = "error"
                    sub.error_output = traceback.format_exc()[:5000]
                    db.commit()
        except Exception:
            traceback.print_exc()
        finally:
            db.close()
        time.sleep(POLL_INTERVAL_SECONDS)


def start_background_worker():
    """Call once at FastAPI startup to begin polling for pending submissions."""
    thread = threading.Thread(target=_poll_loop, daemon=True, name="judge-poller")
    thread.start()
