from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case, distinct
from app.core.database import get_db
from app.models.user import User
from app.models.submission import Submission
from app.models.problem import Problem

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

@router.get("/submissions")
def leaderboard_stats(db: Session = Depends(get_db)):
    """Return aggregated, public leaderboard stats per user.
    Only exposes: username, solved count (by difficulty), total submissions,
    accepted count, accuracy, languages used.
    Does NOT expose individual submission details, timestamps, or user IDs —
    submissions are private by default (see FAQ)."""

    # ── Build problem difficulty lookup ────────────────────────────────
    prob_rows = db.query(Problem.id, Problem.difficulty).all()
    prob_diff = {p.id: (p.difficulty or "unknown").lower() for p in prob_rows}

    # ── Fetch only the columns we need (no code, no timestamps) ───────
    rows = db.query(
        Submission.user_id,
        Submission.problem_id,
        Submission.verdict,
        Submission.language,
        User.username,
    ).join(User, User.id == Submission.user_id).filter(
        Submission.is_sample_only == False
    ).all()

    # ── Aggregate per user ────────────────────────────────────────────
    by_user = {}
    for r in rows:
        if r.user_id not in by_user:
            by_user[r.user_id] = {
                "username": r.username,
                "subs": [],
            }
        by_user[r.user_id]["subs"].append(r)

    result = []
    for uid, u in by_user.items():
        subs = u["subs"]
        total = len(subs)
        accepted = sum(1 for s in subs if s.verdict == "accepted")
        accuracy = round((accepted / total) * 100) if total else 0

        # Unique solved problems by difficulty
        solved_ids = {"easy": set(), "medium": set(), "hard": set(), "unknown": set()}
        for s in subs:
            if s.verdict == "accepted":
                diff = prob_diff.get(s.problem_id, "unknown")
                solved_ids.get(diff, solved_ids["unknown"]).add(s.problem_id)

        solved = sum(len(v) for v in solved_ids.values())
        langs = list({s.language for s in subs if s.language})

        result.append({
            "username": u["username"],
            "solved": solved,
            "total": total,
            "accepted": accepted,
            "accuracy": accuracy,
            "easy": len(solved_ids["easy"]),
            "medium": len(solved_ids["medium"]),
            "hard": len(solved_ids["hard"]),
            "langs": langs,
        })

    # Sort by solved desc, then accuracy desc
    result.sort(key=lambda x: (-x["solved"], -x["accuracy"]))
    return result


@router.get("/users")
def all_users_for_leaderboard(db: Session = Depends(get_db)):
    """Return basic public info for all users."""
    users = db.query(User.id, User.username).all()
    return [{"id": u.id, "username": u.username} for u in users]
